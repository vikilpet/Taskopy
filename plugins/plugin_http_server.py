import time
import os
import re
from hashlib import md5
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib
import tempfile


_TASK_TIMEOUT = 60

if __name__ == '__main__':
	from tools import msgbox_warning, random_str
else:
	from .tools import msgbox_warning, random_str

class RequestData:
	''' To keep HTTP request data in instance instead of dictionary
	'''
	def __init__(s, client_ip:str, path:str
					, headers:dict={}, params:dict={}
					, post_file:str=None):
		''' client_ip - str
			path - '/task_name'
			headers - HTTP request headers
			params - 'par1':'123'
		'''
		s.client_ip = client_ip
		s.path = path
		s.post_file = post_file
		s.__dict__.update(headers)
		s.__dict__.update(params)

	def __getattr__(s, name):
		return 'unknown property'

class HTTPHandlerTasks(BaseHTTPRequestHandler):
	def __init__(s, request, client_address, server
				, tasks):
		s.silent = True
		s.tasks = tasks
		super().__init__(request, client_address, server)

	def s_print(s, text:str, data:str=''):
		now = time.time()
		year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
		time_str = f'{day:02}-{month:02}-{year} {hh:02}:{mm:02}:{ss:02}'
		if s.silent:
			print(f'{time_str} {text}')
		else:
			print(f'{time_str} {text} {data}')
	
	def handle_one_request(s):
		try:
			super().handle_one_request()
			my_req = str(s.raw_requestline, 'iso-8859-1').split()[0].upper()
			if not my_req in ('GET', 'POST'):
				s.s_print(
					f'{s.address_string()} wrong HTTP request'
					+ f' ({len(my_req)}): {my_req[:20]}'
				)
		except Exception as e:
			if sett.dev: raise
			if not s.silent:
				s.s_print(
					f'{s.address_string()} handle_one_request'
					+ f' exception: {repr(e)[:150]}'
				)
				
	def white_list_check(s):
		if not sett.white_list: return True
		if s.address_string() in sett.white_list.split(','):
			return True
		if sett.dev:
			s.log_message(
				f'Request from unknown IP ({s.address_string()}): {s.path[:20]}'
			)
		return False

	def headers_and_page(s, page:str, status:int=200):
		''' Write headers and page
		'''
		s.send_response(status)
		s.send_header('Content-Type', 'text/plain; charset=utf-8')
		s.end_headers()
		s.wfile.write(bytes(page, 'utf-8'))

	def launch_task(s, request_type:str):
		def start_data_processing(http_dir:str=None):
			''' Launch data_processing and calculate hash. '''
			status, data, file_hash_header = s.data_processing(http_dir)
			if status:
				fullpath = data
				if not file_hash_header:
					return True, fullpath
				file_hash_local = _file_hash(fullpath)
				if file_hash_local == file_hash_header:
					return True, fullpath
				else:
					return False, 'hashes do not match'
			else:
				return False, data
		if not s.white_list_check():
			s.headers_and_page('403')
			return
		if not s.path.startswith('/task?'):
			s.headers_and_page('unknown request')
		try:
			params = {
				key:urllib.parse.unquote(value[0])
					for key, value in
						urllib.parse.parse_qs(s.path).items()
			}
		except Exception as e:
			s.s_print(f'Bad HTTP query format: {repr(e)}')
			s.headers_and_page('error')
			return
		page = 'error'
		task_name = s.path.split('?')[1].split('&')[0]
		for task in s.tasks.task_list_http:
			if task['task_function_name'] != task_name: continue
			post_file = None
			if request_type == 'POST':
				status, post_file = start_data_processing(
					http_dir=task['http_dir']
				)
				if not status:
					s.s_print(f'data_processing error: {post_file}')
					s.headers_and_page('error')
					return
			try:
				req_data = RequestData(
					client_ip=s.client_address[0]
					, path=s.path
					, headers=dict(s.headers)
					, params=params
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
				break
			except Exception as e:
				s.s_print(f'HTTP task exception: {repr(e)}')
				page = 'error'
		else:
			s.s_print('task not found')
			page = 'task not found'
		s.headers_and_page(page)

	def do_GET(s):
		if 'favicon.' in s.path:
			if sett.dev: s.s_print(f'favicon request: {s.path}')
			s.wfile.write(b'<link rel="icon" href="data:,">')
			return
		s.launch_task('GET')
		
	def data_processing(s, http_dir:str=None)->tuple:
		''' Writes file on disk, calculates MD5 if 'Content-MD5'
			header exist.
			Returns: status, fullpath, md5 or status, error, None
		'''
		try:
			content_type = s.headers.get('Content-Type', None)
			if not content_type:
				return False, "Content-Type does not exist", None
			boundary = content_type.split('=')[1].encode()
			remainbytes = int(s.headers['Content-Length'])
			line = s.rfile.readline()
			remainbytes -= len(line)
			if not boundary in line:
				return False, 'Content not begin with boundary', None
			line = s.rfile.readline()
			remainbytes -= len(line)
			file_name = re.findall(r'Content-Disposition.*name="file";'
								+' filename="(.*)"', line.decode())
			if not http_dir: http_dir = tempfile.gettempdir()
			if file_name:
				fullpath = http_dir + '\\' + file_name[0]
			else:
				fullpath = (http_dir + '\\'
					+ time.strftime('%m%d%H%M%S') + random_str(5))
			line = s.rfile.readline()
			remainbytes -= len(line)
			with open(fullpath, 'bw+') as file_desc:
				preline = s.rfile.readline()
				remainbytes -= len(preline)
				while remainbytes > 0:
					line = s.rfile.readline()
					remainbytes -= len(line)
					if boundary in line:
						preline = preline[0:-1]
						if preline.endswith(b'\r'):
							preline = preline[0:-1]
						file_desc.write(preline)
						break
					else:
						file_desc.write(preline)
						preline = line
			return True, fullpath, s.headers.get('Content-MD5', None)
		except Exception as e:
			return False, f'upload error: {repr(e)}', None

	def do_POST(s):
		if sett.dev: s.s_print(s.headers)
		s.launch_task('POST')

	def log_message(s, format, *args):
		if not s.silent: super().log_message(format, *args)


def http_server_start(tasks):
	''' Start HTTP server that will run tasks.
		tasks - instance of Tasks class
	'''
	try:
		httpd = ThreadingHTTPServer(
			(sett.server_ip, sett.server_port)
			, lambda *a, tasks=tasks: HTTPHandlerTasks(*a, tasks=tasks)
		)
		print(
			'The HTTP server is running at'
			+ f' {sett.server_ip}:{sett.server_port}'
		)
		tasks.http_server = httpd
		httpd.serve_forever()
	except Exception as e:
		print(f'HTTP Server error:\n{repr(e)[:200]}')
		msgbox_warning(f'HTTP Server error:\n{repr(e)[:100]}')

def _file_hash(fullpath:str)->str:
	hash_md5 = md5()
	with open(fullpath, 'rb') as fi:
		for chunk in iter(lambda: fi.read(4096), b''):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()

def main():
	''' Just for testing
	'''
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
 
if __name__ == '__main__': main()
