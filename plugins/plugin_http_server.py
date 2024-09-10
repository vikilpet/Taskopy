import time
import os
import fnmatch
import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cgi
import urllib
from typing import Pattern
from .tools import dev_print, app_log_get, DataHTTPReq \
	, patch_import, tprint, value_to_unit, exc_text
from .plugin_filesystem import file_b64_dec, HTTPFile
try:
	import constants as tcon
except ModuleNotFoundError:
	import plugins.constants as tcon

_FAVICON:tuple = tuple()

if __name__ == '__main__':
	from tools import warning, random_str
else:
	from .tools import warning, random_str


class HTTPHandlerTasks(BaseHTTPRequestHandler):
	def __init__(self, request, client_address, server
				, tasks):
		self.silent = True
		self.tasks = tasks
		self.req_data = DataHTTPReq()
		super().__init__(request, client_address, server)

	def s_print(self, text:str, data:str=''):
		if self.silent:
			print('{} {}'.format(
				time.strftime('%y.%m.%d %H:%M:%S'), text))
		else:
			print('{} {} {}'.format(
				time.strftime('%y.%m.%d %H:%M:%S'), text, data))
	
	def handle_one_request(self):
		try:
			super().handle_one_request()
			req_str = str(self.raw_requestline, 'iso-8859-1')
			if len(req_str) < 4:
				dev_print(f'port scan from {self.client_address}')
				return
			req_type = req_str.split()[0].upper()
			if not req_type in ('GET', 'POST', 'HEAD'):
				dev_print(
					f'{self.address_string()[:20]} wrong HTTP request'
					+ f' (total length {len(req_str)}): {req_str[:20]}'
				)
		except Exception as e:
			if sett.dev:
				raise
			elif not self.silent:
				self.s_print(
					f'{self.address_string()} handle_one_request'
					+ f' exception: {repr(e)[:150]}'
				)
				
	def white_list_check(self, task=None)->bool:
		if not sett.white_list: return True
		if isinstance(sett.white_list, str):
			sett.white_list = [
				ip.strip() for ip in sett.white_list.split(',')
			]
		white_list = sett.white_list.copy()
		if task and task.get('http_white_list', None):
			if isinstance(task['http_white_list'], str):
				wl = [ ip.strip() for ip in task['http_white_list'].split(',') ]
			else:
				wl = task['http_white_list']
			white_list.extend(wl)
		for ip in white_list:
			if fnmatch.fnmatch(self.address_string(), ip):
				return True
		if sett.dev:
			self.log_message(
				f'request from unknown IP ({self.address_string()}):' 
				+ f' {self.path[:20]}'
			)
		return False

	def headers_and_page(self, page:str|HTTPFile='', status:int=200):
		r'''
		Write headers and page. 
		*page* - str or HTML or HTTPFile instance.  
		'''
		CHUNK_SIZE = 1024 * 100
		self.send_response(status, 'Ok')
		if not isinstance(page, str) and not hasattr(page, 'HTTPFile'):
			page = str(page)
		if hasattr(page, 'HTTPFile'):
			self.send_header('Content-Type', page.mime_type)
			param = 'attachment' if page.use_save_to else 'inline'
			name = urllib.parse.quote(page.name, encoding='utf-8')
			self.send_header('Content-Disposition'
				, f"{param}; filename*=UTF-8''{name}")
			self.send_header('Content-Length', os.path.getsize(page.fullpath))
		elif '<!doctype html>' in page[:30].lower():
			self.send_header('Content-Type', tcon.MIME_HTML)
		else:
			self.send_header('Content-Type', tcon.MIME_TEXT)
		self.end_headers()
		if hasattr(page, 'HTTPFile'):
			with open(page.fullpath, 'rb') as fd:
				try:
					while True:
						chunk = fd.read(CHUNK_SIZE)
						if not chunk: break
						self.wfile.write(chunk)
				except (ConnectionResetError, ConnectionAbortedError):
					pass
				except Exception as e:
					dev_print(f'connection error: {e}')
		else:
			try:
				self.wfile.write(bytes(page, 'utf-8'))
			except ConnectionAbortedError:
				pass
			except Exception as e:
				dev_print(f'connection exception: {e}')

	def start_data_processing(self)->tuple:
		'''
		Launch *data_processing* and checks file hash if any.  
		Returns (True, None) or (False, error:str)
		'''
		status, error = self.data_processing()
		if not status: return False, error
		if not self.req_data._md5: return True, None
		file_hash_local = _file_hash(self.req_data.file)
		if file_hash_local == self.req_data._md5:
			return True, None
		else:
			return (
				False
				, 'hashes do not match:'
					+ f' local {file_hash_local}'
					+ f' header {self.req_data._md5}'
			)

	def process_req(self, method:str):
		' Parse the URL and decide which action to perform '
		try:
			(
				_, _
				, self.url_path, self.url_query, self.url_fragment
			) = (
				u for u in urllib.parse.urlsplit(self.path)
			)
		except Exception as e:
			dev_print('wrong url:', self.path[:70], 'exception:', str(e))
			self.headers_and_page('wrong url')
			return
		if self.url_path == '/log':
			if self.white_list_check():
				self.headers_and_page(app_log_get())
			else:
				self.headers_and_page('403')
			return
		try:
			params = {
				key : urllib.parse.unquote(value[0])
					for key, value in
						urllib.parse.parse_qs(self.url_query).items()
			}
		except Exception as e:
			self.s_print(f'Bad HTTP query format: {repr(e)}')
			self.headers_and_page('error')
			return
		page = 'error'
		task_path = urllib.parse.unquote( self.url_path.strip('/') )
		task = None
		re_pat: Pattern
		for tdic in self.tasks.task_list_http:
			if not (re_lst := tdic['http_re']): continue
			for re_pat in re_lst:
				if re_pat.match(task_path):
					task = tdic
					break
			if task: break
		else:
			self.s_print('task path not found: "{}"'.format( task_path[:30]) )
			self.headers_and_page('task not found')
			return
		if not self.white_list_check(task=task):
			self.headers_and_page('403')
			return
		self.http_dir = task['http_dir']
		self.req_data.method = method
		self.req_data.client_ip = self.client_address[0]
		self.req_data.path = task_path
		self.req_data.headers = dict(self.headers)
		self.req_data.params = params
		if method == 'POST':
			status, error = self.start_data_processing()
			if not status:
				self.s_print(f'data_processing error: {error}')
				self.headers_and_page('error')
				return
		try:
			if task['result']:
				result = []
				wait_event = threading.Event()
				self.tasks.run_task(
					task
					, caller=tcon.CALLER_HTTP
					, data=self.req_data
					, result=result
					, wait_event=wait_event
				)
				if wait_event.wait(
					value_to_unit( task['timeout'], unit='sec')
				) == True:
					if len(result): page = result[0]
				else:
					page = 'timeout'
			else:
				self.tasks.run_task(
					task
					, caller=tcon.CALLER_HTTP
					, data=self.req_data
				)
				page = 'OK'
		except:
			self.s_print(f'HTTP task exception:\n{exc_text(6)}')
			page = 'error'
		self.headers_and_page(page)

	def do_GET(self):
		global _FAVICON
		if 'favicon.' in self.path:
			if self.white_list_check():
				if not _FAVICON:
					i = file_b64_dec(tcon._APP_FAVICON)
					_FAVICON = (i, str(len(i)))
				self.send_response(200)
				self.send_header('Content-Type', 'image/x-icon')
				self.send_header('Content-Length', _FAVICON[1])
				self.end_headers()
				try:
					self.wfile.write(_FAVICON[0])
				except ConnectionAbortedError:
					dev_print(f'favicon connection aborted')
				except Exception as e:
					dev_print(f'favicon req exception: {e}')
			else:
				dev_print(f'unknown favicon request: {self.path} from {self.client_address}')
				try:
					self.wfile.write(b'<link rel="icon" href="data:,">')
				except Exception as e:
					dev_print(f'favicon req (unknown) exception: {e}')
			return
		self.process_req('GET')
		
	def data_processing(self)->tuple:
		r'''
		Reads form data or file from a POST request.  
		Writes the file on disk (if it big enough).
		Returns (status, None) or (status, error:str)  
		'''
		CHUNK_SIZE = 1_048_576
		BODY_SIZE_MAX = 1_048_576
		self.req_data._fullpath = os.path.join(self.http_dir
		, 'tskphttp' + random_str(5))
		try:
			form_obj: cgi.FieldStorage = None
			if (ct := self.headers['Content-Type']) != None and (
				'form-data' in ct
				or 'x-www-form-urlencoded' in ct
			):
				form_obj = cgi.FieldStorage(
					fp=self.rfile
					, headers=self.headers
					, environ={
						'REQUEST_METHOD': 'POST'
						, 'CONTENT_TYPE': self.headers['Content-Type']
					}
				)
			else:
				cont_len = int( self.headers['Content-Length'] )
				if BODY_SIZE_MAX >= cont_len:
					self.req_data._body = self.rfile.read(cont_len)
					return True, None
				cur_size = 0
				self.req_data._file = self.req_data._fullpath
				with open(self.req_data._fullpath, 'wb') as fd:
					while cur_size < cont_len:
						chunk = self.rfile.read(
							min( CHUNK_SIZE, cont_len - cur_size )
						)
						fd.write(chunk)
						cur_size += CHUNK_SIZE
				return True, None
			for key in form_obj.keys():
				if key == 'file': continue
				if key == 'editable':
					self.req_data.form[key] = (form_obj.getfirst(key) == 'true')
				elif form_obj.getfirst(key) == 'undefined':
					self.req_data.form[key] = None
				else:
					self.req_data.form[key] = form_obj.getfirst(key)
			self.req_data._form_upd()
			if form_obj.getvalue('file', None):
				if form_obj['file'].file is None:
					return False, 'error: form file is None'
				filename = form_obj['file'].filename
				if not filename:
					filename = time.strftime('%m%d%H%M%S') + random_str(5)
				self.req_data._fullpath = os.path.join(self.http_dir, filename)
				self.req_data._file = self.req_data._fullpath
				with open(self.req_data._fullpath, 'wb') as fd:
					fd.write(form_obj['file'].file.read())
			self.req_data._md5 = self.headers.get('Content-MD5', '')
			return True, None
		except:
			return False, f'upload error: {exc_text(6)}'

	def do_POST(self):
		self.process_req('POST')

	def log_message(self, msg_format, *args):
		if not self.silent:
			super().log_message(msg_format, *args)

def http_server_start(tasks):
	''' Starts HTTP server that will run 'tasks'.
		tasks - instance of 'Tasks' class.
	'''
	try:
		httpd = ThreadingHTTPServer(
			(sett.server_ip, sett.server_port)
			, lambda *a, tasks=tasks: HTTPHandlerTasks(*a, tasks=tasks)
		)
		tprint(
			'The HTTP server is running at'
			+ f' {sett.server_ip}:{sett.server_port}'
		)
		tasks.http_server = httpd
		httpd.serve_forever()
	except Exception as e:
		print(f'HTTP server error:\n{repr(e)}')
		warning(f'HTTP server error:\n{repr(e)}')
def _file_hash(fullpath:str)->str:
	hash_md5 = hashlib.md5()
	with open(fullpath, 'rb') as fi:
		for chunk in iter(lambda: fi.read(1_048_576), b''):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()
 
if __name__ == '__main__':
	print('Test http task handler')
	serv_ip = '127.0.0.1'
	serv_port = 88
	try:
		server_address = (serv_ip, serv_port)
		httpd = ThreadingHTTPServer(server_address, HTTPHandlerTasks)
		print(
			f'The server is running at {serv_ip}:{serv_port}'
		)
		httpd.serve_forever()
	except KeyboardInterrupt:
		print('\nTerminated by keyboard')
	except Exception as e:
		print(f'General error: {repr(e)[:100]}')
else:
	patch_import()
