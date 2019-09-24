import subprocess
import os
import ctypes
import psutil
import time
import win32gui
import win32api
import win32con
from .tools import DictToObj, dev_print

# https://psutil.readthedocs.io/en/latest/

_SIZE_UNITS = {'gb':1073741824, 'mb':1048576, 'kb':1024, 'b':1, 'percent':1}

def file_open(fullpath:str, showcmd:int=win32con.SW_SHOWNORMAL):
	''' Open file or URL in default program
	'''
	win32api.ShellExecute(None, 'open', fullpath, None, None, showcmd)

def process_get(process)->int:
	''' Returns PID of process.
	'''
	if type(process) is int: return process
	name = process.lower()
	for proc in psutil.process_iter():
		if proc.name().lower() == name: return proc.pid
	return False

def app_start(
	app_path:str
	, app_args=None
	, wait:bool=False
	, capture_output:bool=False
	, encoding:str='cp866'
	, shell:bool=False
	, cwd:str=None
	, env:dict=None
	, hidden:bool=False
	, minimized:bool=False
	, maximized:bool=False
):
	''' Starts application.
		Returns:
			if capture_output - returncode, stdout, stderr
			if wait - returncode
			otherwise - PID of new process.
		app_path - path to file or path to executable. Do not add
		double quotes.
		app_args (list or str) - command-line parameters.
		cwd - working directory.
		wait - wait for execution.
		capture_output - capture stdout and stderr.
		env - add this environments to the process

		https://docs.python.org/3/library/subprocess.html
	'''

	if type(app_path) is str:
		app_path = [app_path]
	elif not type(app_path) is list:
		raise 'Unknown type of app_path'
	if app_args:
		if type(app_args) is str:
			app_path += app_args.split()
		elif type(app_args) is list:
			app_path += app_args
		else:
			raise 'Unknown type of app_args'
	info = subprocess.STARTUPINFO()
	info.dwFlags = subprocess.STARTF_USESHOWWINDOW
	if minimized:
		info.wShowWindow = win32con.SW_SHOWMINNOACTIVE
	elif maximized:
		info.wShowWindow = win32con.SW_SHOWMAXIMIZED
	elif hidden:
		info.wShowWindow = win32con.SW_HIDE
	else:
		info.wShowWindow = win32con.SW_SHOWNORMAL
	proc_args = {
		'args': app_path
		, 'shell': shell
		, 'close_fds': True
		, 'cwd': cwd
		, 'creationflags': win32con.DETACHED_PROCESS
		, 'startupinfo': info
	}
	if env:
		env = {**os.environ, **env}
		proc_args['env'] = env
	if capture_output: wait=True
	if wait:
		proc_func = subprocess.run
		if capture_output:
			proc_args['shell'] = False
			proc_args['capture_output'] = True
			proc_args['text'] = True
			proc_args['encoding']: encoding
	else:
		proc_func = subprocess.Popen
	r = proc_func(**proc_args)
	if wait:
		if capture_output:
			return r.returncode, r.stdout, r.stderr
		else:
			return r.returncode
	else:
		return r.pid

def process_exist(process, cmd:str=None)->bool:
	''' Returns PID if the process with the specified name exists.
		process - image name or PID.
		cmd - optional string to search in the command line of the process.
	'''
	pid = process_get(process)
	if cmd: cmd=cmd.lower()
	for proc in psutil.process_iter():
		if proc.pid == pid:
			if cmd:
				if cmd in ' '.join(proc.cmdline()):	return proc.pid
			else:
				return pid
	return False

def process_list(name:str='')->list:
	''' Returns list of dicts with process information.
		name - image name. If not specified then list all
			processes.
		Process information includes: pid:int, name:str
		, username:str, exe:str, cmdline:list

	'''
	ATTRS=['pid', 'name', 'username', 'exe', 'cmdline']

	name = name.lower()
	proc_list = []
	for proc in psutil.process_iter():
		if name:
			if proc.name().lower() == name:
				di = proc.as_dict(attrs=ATTRS)
				di['cmdline'] = list(di['cmdline'])
				proc_list.append( DictToObj(di) )
		else:
			di = proc.as_dict(attrs=ATTRS)
			di['cmdline'] = list(di['cmdline'])
			proc_list.append( DictToObj(di) )
	return proc_list

def process_cpu(pid:int, interval:int=1)->float:
	''' Returns CPU usage of specified PID for specified interval
		of time in seconds.
	'''
	try:
		proc = psutil.Process(pid)
		return proc.cpu_percent(interval)
	except psutil.NoSuchProcess:
		return 0

def process_kill(process):
	''' Kills the prosess.
	'''
	if type(process) == int:
		try:
			psutil.Process(process).kill()
		except ProcessLookupError:
			if sett.dev: print(f'PID {process} not found')
	elif type(process) == str:
		name = process.lower()
		for proc in psutil.process_iter(attrs=['name']):
			if proc.name().lower() == name: proc.kill()
	else:
		raise ValueError(
			f'Unknown type of "process" argument: {type(process)}'
		)

def free_ram(unit:str='percent'):
	'''	Returns free RAM size.
		unit - gb, mb... or 'percent'
	'''
	e = _SIZE_UNITS.get(unit.lower(), 1)
	if unit == 'percent':
		return round(100 - psutil.virtual_memory()[2], 1)
	else:
		return psutil.virtual_memory()[4] // e

GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
def process_close(process, timeout:int=10):
	''' Kill process 'softly'. Returns 'True' if process was closed 'softly'
		and False if process was killed after timeout.
	'''
	def find_proc(hwnd, pid):
		cur_pid = ctypes.c_int()
		GetWindowThreadProcessId(hwnd, ctypes.byref(cur_pid))
		if cur_pid.value == pid: windows.append(hwnd)
	pid = process_get(process)
	if not pid: return False
	windows = []
	win32gui.EnumWindows(find_proc, pid)
	if not windows: return False
	for hwnd in windows:
		win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
	for _ in range(timeout):
		time.sleep(1)
		if not psutil.pid_exists(pid): return True
	try:
		psutil.Process(pid).kill()
	except ProcessLookupError:
		dev_print(f'PID {process} not found')
	return False

