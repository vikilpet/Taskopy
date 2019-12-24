import subprocess
import os
import ctypes
import psutil
import time
import win32gui
import win32api
import win32con
import win32com
import win32process
import win32security
import win32ts
import win32serviceutil
from .tools import DictToObj, dev_print, msgbox, tprint
from .plugin_filesystem import path_exists

# https://psutil.readthedocs.io/en/latest/

_SIZE_UNITS = {'gb':1073741824, 'mb':1048576, 'kb':1024, 'b':1, 'percent':1}

def file_open(fullpath:str, operation:str='open', parameters:str=None
, cwd:str=None, showcmd:int=win32con.SW_SHOWNORMAL):
	''' Open file or URL in an associated application.
		If 'file' is executable:
			parameters - commandline parameters
				to be passed to the application.
		operation - operation to perform. With executable
			use 'runas' for elevation.
		cwd - working directory.
		showcmd - how application should be
			displayed. For example:
			3 - maximized (win32con.SW_SHOWMAXIMIZED)
			7 - minimized (win32con.SW_SHOWMINNOACTIVE)
			0 - hidden (win32con.SW_HIDE)
	'''
	win32api.ShellExecute(None, operation.lower(), fullpath
	, parameters, cwd, showcmd)

def process_get(process)->int:
	''' Returns PID of process.
	'''
	if isinstance(process, int): return process
	name = process.lower()
	if not name.endswith('.exe'): name = name + '.exe'
	for proc in psutil.process_iter():
		if proc.name().lower() == name: return proc.pid
	return False

def app_start(
	app_path:str
	, app_args=None
	, wait:bool=False
	, capture_output:bool=False
	, encoding:str=None
	, shell:bool=False
	, cwd:str=None
	, env:dict=None
	, window:str=None
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
		window - maximized, minimized or hidden.

		https://docs.python.org/3/library/subprocess.html
	'''

	if isinstance(app_path, str):
		app_path = [app_path]
	elif not isinstance(app_path, list):
		raise 'Unknown type of app_path'
	if app_args:
		if isinstance(app_args, str):
			app_path += app_args.split()
		elif isinstance(app_args, list):
			app_path += app_args
		else:
			raise 'Unknown type of app_args'
	if not cwd:
		if ':\\' in app_path[0]:
			cwd = os.path.dirname(app_path[0])
	startupinfo = subprocess.STARTUPINFO()
	creationflags = win32con.DETACHED_PROCESS
	startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
	if window:
		window = window.lower()
	else:
		window = 'normal'
	if window == 'minimized':
		startupinfo.wShowWindow = win32con.SW_SHOWMINNOACTIVE
	elif window == 'maximized':
		startupinfo.wShowWindow = win32con.SW_SHOWMAXIMIZED
	elif window == 'hidden':
		creationflags |= win32process.CREATE_NO_WINDOW
		startupinfo.wShowWindow = win32con.SW_HIDE
	else:
		startupinfo.wShowWindow = win32con.SW_SHOWNORMAL
	proc_args = {
		'args': app_path
		, 'shell': shell
		, 'close_fds': True
		, 'cwd': cwd
		, 'creationflags': creationflags
		, 'startupinfo': startupinfo
		, 'encoding': encoding
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
		cmd - optional string to search in the
			command line of the process.
	'''
	if cmd: cmd=cmd.lower()
	if isinstance(process, str): process = process.lower()
	for proc in psutil.process_iter():
		try:
			if isinstance(process, str):
				if proc.name().lower() == process:
					if cmd:
						if cmd in ' '.join(proc.cmdline()).lower():
							return proc.pid
					else:
						return proc.pid
			else:
				if proc.pid == process:
					if cmd:
						if cmd in ' '.join(proc.cmdline()).lower(): return proc.pid
					else:
						return proc.pid
		except psutil.AccessDenied:
			dev_print(f'proc_exist access denied: {process}')
	return False

def process_list(name:str='', cmd_filter:str=None)->list:
	''' Returns list of DictToObj with process information.
		name - image name. If not specified then list all
			processes.
		cmd_filter - a substring to look for in command line.
		Process information includes: pid:int, name:str
		, username:str, fullpath:str, cmdline:list
		, cmdline_str:str.
		You may need admin rights to read info for every
		process.
		All strings in lowercase.
	'''
	ATTRS=['pid', 'name', 'username', 'exe', 'cmdline']
	name = name.lower()
	if cmd_filter: cmd_filter = cmd_filter.lower()
	proc_list = []
	for proc in psutil.process_iter():
		if name:
			if proc.name().lower() != name: continue
		di = proc.as_dict(attrs=ATTRS)
		for key in di:
			if isinstance(di[key], str):
				di[key] = di[key].lower()
		if di['cmdline']:
			li = [i.lower() for i in di['cmdline']]
			di['cmdline'] = li
			di['cmdline_str'] = ' '.join(li)
			if cmd_filter:
				if not cmd_filter in di['cmdline_str']:
					continue
		if di['username']:
			di['username'] = di['username'].split('\\')[1]
		di['fullpath'] = di.get('exe', None)
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
	if isinstance(process, int):
		try:
			psutil.Process(process).kill()
		except ProcessLookupError:
			if sett.dev: print(f'PID {process} not found')
	elif isinstance(process, str):
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


def process_close(process, timeout:int=10):
	''' Kills the process 'softly'. Returns 'True' if process
		was closed 'softly' and False if process was killed
		after timeout.
	'''
	def collect_windows(hwnd, param=None):
		nonlocal windows
		windows.append(hwnd)
		return True
	pid = process_get(process)
	if not pid: return False
	windows = []
	try:
		for thread in psutil.Process(pid).threads():
			win32gui.EnumThreadWindows(thread.id, collect_windows, None)
	except psutil.NoSuchProcess:
		dev_print('process is gone')
		pass
	for hwnd in windows:
		try:
			win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
		except Exception as e:
			dev_print(f'postmessage error: {repr(e)}')
	for _ in range(timeout):
		time.sleep(1)
		if not psutil.pid_exists(pid): return True
	try:
		psutil.Process(pid).kill()
	except ProcessLookupError:
		dev_print(f'PID {pid} was not found')
	return False

def wts_message(sessionid:int, msg:str, title:str, style:int=0
, timeout:int=0, wait:bool=False)->int:
	''' Sends message to WTS session.
		style - styles like in MessageBox (0 - MB_OK).
		timeout - timeout in seconds (0 - no timeout).
		Returns same values as MessageBox.
	'''
	return win32ts.WTSSendMessage(0, sessionid
	, msg, title, style, timeout, wait)
	
def wts_cur_sessionid()->int:
	''' Returns SessionID of current process.
	'''
	return win32ts.ProcessIdToSessionId(win32api.GetCurrentProcessId())

def wts_logoff(sessionid:int, wait:bool=False)->int:
	''' Logoffs session. wait - wait for completion.
		If the function fails, the return value is zero.
	'''
	return win32ts.WTSLogoffSession(0, sessionid, wait)
	
def wts_proc_list(process:str=None)->list:
	''' Returns list of DictToObj objects with properties:
		.sessionid:int, .pid:int, .process:str (name of exe file)
		, .pysid:obj, .username:str, .cmdline:list
		process - filter by process name.
	'''
	if process: process = process.lower()
	proc_tup = win32ts.WTSEnumerateProcesses()
	proc_li = []
	for tup in proc_tup:
		if process:
			if tup[2].lower() != process: continue
		di = {}
		di['sessionid'], di['pid'], di['process'], _ = tup
		di['process'] = di['process'].lower()
		proc = psutil.Process(di['pid'])
		di['username'] = proc.username()
		if di['username']:
			di['username'] = di['username'].split('\\')[1].lower()
		di['cmdline'] = proc.cmdline()
		proc_li.append(DictToObj(di))
	return proc_li

def service_running(service:str)->bool:
	'''Returns True if servise is running.'''
	return win32serviceutil.QueryServiceStatus(service)[1] == 4

def service_start(service:str, args:tuple=None):
	''' Starts windows service.'''
	win32serviceutil.StartService(service, args)

def service_stop(service:str)->tuple:
	''' Stops windows service.'''
	return win32serviceutil.StopService(service)








