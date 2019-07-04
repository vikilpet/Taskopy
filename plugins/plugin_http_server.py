import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib
from .tools import msgbox_warning

class HTTPHandlerTasks(BaseHTTPRequestHandler):
	def __init__(s, request, client_address, server
				, tasks, settings):
		s.silent = settings.server_silent
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
					result = s.tasks.run_task(
						task
						, caller='http'
						, data={
							'headers':dict(s.headers)
							, 'client_ip':s.client_address[0]
							, 'path':s.path
							, 'params':params
						}
					)
					page = str(result) if result else 'OK'
					break
			else:
				page = 'task not found'
		else:
			page = 'unknown request'
		s.wfile.write(bytes(page, 'utf-8'))

	def log_message(s, format, *args):
		if not s.silent: super().log_message(format, *args)


def http_server_start(settings, tasks):
	''' Start HTTP server that will run tasks.
		settings - instance of Settings class
		tasks - instance of Tasks class
	'''
	try:
		httpd = ThreadingHTTPServer(
			(settings.server_ip, int(settings.server_port))
			, lambda *a, settings=settings, tasks=tasks:
				HTTPHandlerTasks(*a, settings=settings, tasks=tasks)
		)
		print(
			'Start HTTP-server on'
			+ f' {settings.server_ip}:{settings.server_port}'
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
