import time
import os
import re
import fnmatch
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cgi
import urllib
import tempfile
from .tools import *
from .plugin_filesystem import file_b64_dec
from .constants import _APP_FAVICON


_TASK_TIMEOUT = 60
_FAVICON = None

if __name__ == '__main__':
	from tools import msgbox_warning, random_str
else:
	from .tools import msgbox_warning, random_str


class HTTPHandlerTasks(BaseHTTPRequestHandler):
	def __init__(s, request, client_address, server
				, tasks):
		s.silent = True
		s.tasks = tasks
		super().__init__(request, client_address, server)

	def s_print(s, text:str, data:str=''):
		if s.silent:
			print('{} {}'.format(
				time.strftime('%y.%m.%d %H:%M:%S'), text))
		else:
			print('{} {} {}'.format(
				time.strftime('%y.%m.%d %H:%M:%S'), text, data))
	
	def handle_one_request(s):
		try:
			super().handle_one_request()
			my_req = str(s.raw_requestline, 'iso-8859-1').split()[0].upper()
			if not my_req in ('GET', 'POST'):
				s.s_print(
					f'{s.address_string()[:20]} wrong HTTP request'
					+ f' ({len(my_req)}): {my_req[:20]}'
				)
		except Exception as e:
			if sett.dev:
				raise
			elif not s.silent:
				s.s_print(
					f'{s.address_string()} handle_one_request'
					+ f' exception: {repr(e)[:150]}'
				)
				
	def white_list_check(s, task=None)->bool:
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
			if fnmatch.fnmatch(s.address_string(), ip):
				return True
		if sett.dev:
			s.log_message(
				f'Request from unknown IP ({s.address_string()}): {s.path[:20]}'
			)
		return False

	def headers_and_page(s, page:str, status:int=200):
		''' Write headers and page.
		'''
		s.send_response(status)
		if '<!doctype html>' in page[:30].lower():
			s.send_header('Content-Type', 'text/html; charset=utf-8')
		else:
			s.send_header('Content-Type', 'text/plain; charset=utf-8')
		s.end_headers()
		s.wfile.write(bytes(page, 'utf-8'))

	def launch_task(s, request_type:str):
		
		def start_data_processing(http_dir:str=None)->tuple:
			''' Launch data_processing and calculate hash.
				Returns (True, data:dict, fullpath:str) or
				(False, error:str, None)
			'''
			status, data, fullpath, file_hash_header = \
				s.data_processing(http_dir)
			if status:
				if not file_hash_header:
					return True, data, fullpath
				file_hash_local = _file_hash(fullpath)
				if file_hash_local == file_hash_header:
					return True, data, fullpath
				else:
					return (
						False
						, 'hashes do not match:'
							+ f' local {file_hash_local}'
							+ f' header {file_hash_header}'
						, None
					)
			else:
				return False, data, None
		
		try:
			(
				_, _
				, s.url_path, s.url_query, s.url_fragment
			) = (
				u for u in urllib.parse.urlsplit(s.path)
			)
		except Exception as e:
			dev_print('wrong url:', s.path[:70], 'exception:', str(e))
			s.headers_and_page('wrong url')
			return
		if not s.url_path in ['/task', '/log']:
			s.headers_and_page('unknown request')
			return
		if s.url_path == '/log':
			if not s.white_list_check():
				s.headers_and_page('403')
				return
			s.headers_and_page(app_log_get())
			return
		try:
			params = {
				key : urllib.parse.unquote(value[0])
					for key, value in
						urllib.parse.parse_qs(s.path).items()
			}
		except Exception as e:
			s.s_print(f'Bad HTTP query format: {repr(e)}')
			s.headers_and_page('error')
			return
		page = 'error'
		task_name = urllib.parse.unquote(
			s.url_query.split('&')[0] )
		task = None
		for t in s.tasks.task_list_http:
			if task_name == t['task_function_name']:
				task = t
				break
		else:
			s.s_print('task not found:', task_name[:30])
			s.headers_and_page('task not found')
			return
		if not s.white_list_check(task=task):
			s.headers_and_page('403')
			return
		post_file = None
		form_data = {}
		if request_type == 'POST':
			status, data, post_file = start_data_processing(
				http_dir=task['http_dir'])
			if not status:
				s.s_print(f'data_processing error: {data}')
				s.headers_and_page('error')
				return
			form_data = data
		try:
			req_data = DataHTTPReq(
				client_ip=s.client_address[0]
				, path=s.path, headers=dict(s.headers)
				, params=params, form_data=form_data
				, post_file=post_file
			)
			if task['result']:
				result = []
				s.tasks.run_task(
					task
					, caller='http'
					, data=req_data
					, result=result
				)
				i = 0
				timeout = 0.001
				page = 'Timeout'
				while (not result) and (i < (_TASK_TIMEOUT / timeout)):
					i += 1
					time.sleep(timeout)
				if result: page = str(result[0])
			else:
				s.tasks.run_task(
					task
					, caller='http'
					, data=req_data
				)
				page = 'OK'
		except Exception as e:
			s.s_print(f'HTTP task exception: {repr(e)}')
			page = 'error'
		s.headers_and_page(page)

	def do_GET(s):
		global _FAVICON
		if 'favicon.' in s.path:
			if s.white_list_check():
				if not _FAVICON: _FAVICON = file_b64_dec(_APP_FAVICON)
				s.wfile.write(_FAVICON)
			else:
				dev_print(f'unknown favicon request: {s.path}')
				s.wfile.write(b'<link rel="icon" href="data:,">')
			return
		s.launch_task('GET')
		
	def data_processing(s, http_dir:str=None)->tuple:
		''' Reads form data and file from POST request.
			Writes file on disk, calculates MD5 if 'Content-MD5'
			header exists.
			Returns (status, data:dict, fullpath:str, MD5:str)
			or (status, error:str, None, None)
		'''
		try:
			form = cgi.FieldStorage(
				fp=s.rfile,
				headers=s.headers,
				environ={
					'REQUEST_METHOD': 'POST'
					, 'CONTENT_TYPE': s.headers['Content-Type']
			 	}
			)
			data = {}
			for key in form.keys():
				if key == 'file': continue
				if key == 'editable':
					data[key] = (form.getfirst(key) == 'true')
				elif form.getfirst(key) == 'undefined':
					data[key] = ''
				else:
					data[key] = form.getfirst(key)
			filename = None
			if form.getvalue('file', None):
				if form['file'].file is None:
					return False, 'File is None', None, None
				filename = form['file'].filename
				if not filename:
					filename = time.strftime('%m%d%H%M%S') + random_str(5)
				filename = os.path.join(http_dir, filename)
				with open(filename, "wb") as fd:
					fd.write(form['file'].file.read())
			return True, data, filename, s.headers.get('Content-MD5', None)
		except Exception as e:
			return False, f'upload error: {repr(e)}', None, None

	def do_POST(s):
		s.launch_task('POST')

	def log_message(s, msg_format, *args):
		if not s.silent:
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
	serv_port = 80
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
