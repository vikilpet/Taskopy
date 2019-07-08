import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib
from .tools import msgbox_warning

class RequestData():
	''' To keep HTTP request data in instance instead of dictionary
	'''
	def __init__(s, client_ip:str, path:str
					, headers:dict={}, params:dict={}):
		''' client_ip - str
		'''
		s.client_ip = client_ip
		s.path = path
		s.__dict__.update(headers)
		s.__dict__.update(params)

	def __getattr__(s, name):
		return ''

class HTTPHandlerTasks(BaseHTTPRequestHandler):
	def __init__(s, request, client_address, server
				, tasks, sett):
		s.silent = sett.server_silent
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
			my_req = str(s.raw_requestline, 'iso-8859-1')
			if my_req[:4] != 'GET ':
				if not s.silent:
					s.s_print(
						f'{s.address_string()} wrong HTTP request'
						+ f' ({len(my_req)}): {my_req[:20]}'
					)
		except Exception as e:
			if not s.silent:
				s.s_print(
					f'{s.address_string()} handle_one_request'
					+ f' exception: {repr(e)[:150]}'
				)
	
	def do_GET(s):
		if (
			s.path.endswith('favicon')
			or s.path.endswith('favicon.ico')
			or s.path.endswith('favicon.png')
		): return

		s.send_response(200)
		
		s.send_header('Content-type','text/html; charset=utf-8')
		s.end_headers()
		if s.path.startswith('/task?'):
			try:
				params = {
					key:urllib.parse.unquote(value[0])
						for key, value in
							urllib.parse.parse_qs(s.path).items()
				}
			except Exception as e:
				print(f'Bad HTTP query format:\n{repr(e)}')
				params = {}
			task_name = s.path.split('?')[1].split('&')[0]
			for task in s.tasks.task_list_http:
				if task['task_function_name'] == task_name:
					try:
						req_data = RequestData(
							client_ip=s.client_address[0]
							, path=s.path
							, headers=dict(s.headers)
							, params=params
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
							while (not result) and (i < (10 / timeout)):
								i += 1
								time.sleep(timeout)
							page = str(result[0]) if result else page
						else:
							s.tasks.run_task(
								task
								, caller='http'
								, data=req_data
							)
							page = 'OK'
					except Exception as e:
						print('HTTP task exception: {repr(e)}')
						page = 'Error'
					break
			else:
				page = 'task not found'
		else:
			page = 'unknown request'
		s.wfile.write(bytes(page, 'utf-8'))

	def log_message(s, format, *args):
		if not s.silent: super().log_message(format, *args)


def http_server_start(sett, tasks):
	''' Start HTTP server that will run tasks.
		sett - instance of Settings class
		tasks - instance of Tasks class
	'''
	try:
		httpd = ThreadingHTTPServer(
			(sett.server_ip, int(sett.server_port))
			, lambda *a, sett=sett, tasks=tasks:
				HTTPHandlerTasks(*a, sett=sett, tasks=tasks)
		)
		print(
			'Start HTTP-server on'
			+ f' {sett.server_ip}:{sett.server_port}'
		)
		tasks.http_server = httpd
		httpd.serve_forever()
	except Exception as e:
		print(f'HTTP Server error:\n{repr(e)[:100]}')
		msgbox_warning(f'HTTP Server error:\n{repr(e)[:100]}')
	

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
			'Starting server on '
			+ f'{serv_ip}:{serv_port}'
		)
		httpd.serve_forever()
	except KeyboardInterrupt:
		print('\nTerminated by keyboard')
	except Exception as e:
		print(f'General error: {repr(e)[:100]}')
 
if __name__ == '__main__': main()
