import time
import os
import re
import fnmatch
import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cgi
import urllib
import tempfile
from .tools import dev_print, app_log_get, DataHTTPReq \
	, patch_import, tprint, value_to_unit, exc_text
from .plugin_filesystem import file_b64_dec, HTTPFile
try:
	import constants as tcon
except ModuleNotFoundError:
	import plugins.constants as tcon

_FAVICON = None

if __name__ == '__main__':
	from tools import msgbox_warning, random_str
else:
	from .tools import msgbox_warning, random_str


class HTTPHandlerTasks(BaseHTTPRequestHandler):
	def __init__(self, request, client_address, server
				, tasks):
		self.silent = True
		self.tasks = tasks
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
				dev_print(f'empty request: {req_str}')
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

	def headers_and_page(self, page, status:int=200):
		'''
		Write headers and page.
		*page* - text or HTML or HTTPFile instance.
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
			self.wfile.write(bytes(page, 'utf-8'))

	def process_req(self, method:str):
		' Parse the URL and decide which action to perform '
		
		def start_data_processing(http_dir:str=None)->tuple:
			'''
			Launch data_processing and calculate hash.
			Returns (True, form:dict, fullpath:str) or
			(False, error:str, None)
			'''
			status, form, fullpath, file_hash_header = \
				self.data_processing(http_dir)
			if status:
				if not file_hash_header:
					return True, form, fullpath
				file_hash_local = _file_hash(fullpath)
				if file_hash_local == file_hash_header:
					return True, form, fullpath
				else:
					return (
						False
						, 'hashes do not match:'
							+ f' local {file_hash_local}'
							+ f' header {file_hash_header}'
						, None
					)
			else:
				return False, form, None
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
		task_name = urllib.parse.unquote(
			self.url_path.lstrip('/') )
		task = None
		for t in self.tasks.task_list_http:
			if task_name == t['task_func_name']:
				task = t
				break
		else:
			self.s_print('task not found: {}'.format( task_name[:30]) )
			self.headers_and_page('task not found')
			return
		if not self.white_list_check(task=task):
			self.headers_and_page('403')
			return
		post_file = None
		form = {}
		body = None
		if method == 'POST':
			status, form, post_file = start_data_processing(
				http_dir=task['http_dir'])
			if not status:
				self.s_print(f'data_processing error: {form}')
				self.headers_and_page('error')
				return
			body = form
		try:
			req_data = DataHTTPReq(
				client_ip=self.client_address[0]
				, method=method
				, path=self.path, headers=dict(self.headers)
				, params=params, form_data=form
				, post_file=post_file, body=body
			)
			if task['result']:
				result = []
				wait_event = threading.Event()
				self.tasks.run_task(
					task
					, caller='http'
					, data=req_data
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
					, data=req_data
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
				if not _FAVICON: _FAVICON = file_b64_dec(tcon._APP_FAVICON)
				self.send_response(200)
				self.wfile.write(_FAVICON)
			else:
				dev_print(f'unknown favicon request: {self.path}')
				self.wfile.write(b'<link rel="icon" href="data:,">')
			return
		self.process_req('GET')
		
	def data_processing(self, http_dir:str='')->tuple:
		''' Reads form data or file from a POST request.
			Writes the file on disk, calculates MD5 if 'Content-MD5'
			header exists.
			Returns (status, form:dict, fullpath:str, MD5:str)
			or (status, error:str, None, None)
		'''
		try:
			form_obj: cgi.FieldStorage = None
			if not self.headers['Content-Type']:
				self.headers['Content-Type'] = 'multipart/form-data'
			if 'form-data' in self.headers['Content-Type']:
				form_obj = cgi.FieldStorage(
					fp=self.rfile
					, headers=self.headers
					, environ={
						'REQUEST_METHOD': 'POST'
						, 'CONTENT_TYPE': self.headers['Content-Type']
					}
				)
			else:
				fullpath = os.path.join(
					http_dir
					, time.strftime('%m%d%H%M%S') + random_str(5)
				)
				content = self.rfile.read(
					int( self.headers['Content-Length'] )
				)
				with open(fullpath, 'wb') as fd: fd.write(content)
				return True, {}, fullpath, None
			form = {}
			for key in form_obj.keys():
				if key == 'file': continue
				if key == 'editable':
					form[key] = (form_obj.getfirst(key) == 'true')
				elif form_obj.getfirst(key) == 'undefined':
					form[key] = None
				else:
					form[key] = form_obj.getfirst(key)
			fullpath:str = None
			if form_obj.getvalue('file', None):
				if form_obj['file'].file is None:
					return False, 'error: file is None', None, None
				filename = form_obj['file'].filename
				if not filename:
					filename = time.strftime('%m%d%H%M%S') + random_str(5)
				fullpath = os.path.join(http_dir, filename)
				with open(fullpath, 'wb') as fd:
					fd.write(form_obj['file'].file.read())
			return True, form, fullpath, self.headers.get('Content-MD5', None)
		except:
			return False, f'upload error: {exc_text(6)}', None, None

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
		print(f'HTTP Server error:\n{repr(e)}')
		msgbox_warning(f'HTTP Server error:\n{repr(e)}')
def _file_hash(fullpath:str)->str:
	hash_md5 = hashlib.md5()
	with open(fullpath, 'rb') as fi:
		for chunk in iter(lambda: fi.read(104_857_600), b''):
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
