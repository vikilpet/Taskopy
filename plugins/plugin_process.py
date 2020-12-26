import subprocess
import os
import ctypes
import psutil
import time
import win32gui
import win32api
import win32con
import win32com
import win32event
import win32process
import win32security
import win32ts
import win32serviceutil

import contextlib
import winerror
import pywintypes
import ctypes
from ctypes import wintypes

from .tools import DictToObj, dev_print, msgbox, tprint
from .plugin_filesystem import path_exists

# https://psutil.readthedocs.io/en/latest/

_SIZE_UNITS = {'gb':1073741824, 'mb':1048576, 'kb':1024, 'b':1, 'percent':1}

def file_open(fullpath:str, parameters:str=None, operation:str='open'
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

def process_get(process, cmd_filter:str=None)->int:
	''' Returns PID of process.
		cmd_filter - find process with that
			string in command line.
	'''
	if isinstance(process, int): return process
	if cmd_filter: cmd_filter = cmd_filter.lower()
	name = process.lower()
	if not name.endswith('.exe'): name = name + '.exe'
	for proc in psutil.process_iter():
		try:
			proc_name = proc.name().lower()
		except psutil.AccessDenied as e:
			dev_print('process_get error: ' + repr(e))
			continue
		if proc_name == name:
			if not cmd_filter:
				return proc.pid
			if cmd_filter in ' '.join(proc.cmdline()).lower():
				return proc.pid
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
	, priority:str=None
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
		window - maximized(short - 'max'), minimized('min')
			or hidden('hid').
		priority - 'above', 'below', 'high', 'idle', 'normal'
			or 'realtime'.

		https://docs.python.org/3/library/subprocess.html
	'''

	PRIORITIES = {
		'above': subprocess.ABOVE_NORMAL_PRIORITY_CLASS
		, 'below': subprocess.BELOW_NORMAL_PRIORITY_CLASS
		, 'high': subprocess.HIGH_PRIORITY_CLASS
		, 'idle': subprocess.IDLE_PRIORITY_CLASS
		, 'normal': subprocess.NORMAL_PRIORITY_CLASS
		, 'realtime': subprocess.REALTIME_PRIORITY_CLASS
	}
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
	app_path = list( map(str, app_path) )
	if not cwd:
		if ':\\' in app_path[0]:
			cwd = os.path.dirname(app_path[0])
	startupinfo = subprocess.STARTUPINFO()
	creationflags = win32con.DETACHED_PROCESS
	startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
	if priority:
		creationflags |= PRIORITIES.get(
			priority.lower()
			, subprocess.NORMAL_PRIORITY_CLASS
		)
	if window:
		window = window.lower()
	else:
		window = 'normal'
	if window in ['minimized', 'min']:
		startupinfo.wShowWindow = win32con.SW_SHOWMINNOACTIVE
	elif window in ['maximized', 'max']:
		startupinfo.wShowWindow = win32con.SW_SHOWMAXIMIZED
	elif window in ['hidden', 'hid']:
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
			proc_args['capture_output'] = True
			proc_args['shell'] = False
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

def process_exist(process, cmd_filter:str=None
, user_filter:str=None)->bool:
	''' Returns PID if the process with the specified name exists.
		process - image name or PID.
		cmd_filter - optional string to search in the
			command line of the process.
		user_filter - only search within processes of
			specified user. Format: pc\\username
	'''
	if cmd_filter: cmd_filter = cmd_filter.lower()
	if user_filter: user_filter = user_filter.lower()
	if isinstance(process, str): process = process.lower()
	for proc in psutil.process_iter():
		try:
			if isinstance(process, str):
				if proc.name().lower() == process:
					if user_filter:
						if proc.username().lower() != user_filter: continue
					if cmd_filter:
						if cmd_filter in ' '.join(proc.cmdline()).lower():
							return proc.pid
					else:
						return proc.pid
			else:
				if proc.pid == process:
					if user_filter:
						if proc.username().lower() != user_filter: continue
					if cmd_filter:
						if cmd_filter in ' '.join(proc.cmdline()).lower():
							return proc.pid
					else:
						return proc.pid
		except psutil.AccessDenied:
			dev_print(f'proc_exist access denied: {process}')
	return False

def process_list(name:str='', cmd_filter:str=None
, ad_value=None)->list:
	''' Returns list of DictToObj with process information.
		name - image name. If not specified then list all
			processes.
		cmd_filter - a substring to look for in command line.

		Process information includes: pid:int, name:str
		, username:str, fullpath:str, cmdline:list
		, cmdline_str:str.

        ad_value - is the value which gets assigned in case
        AccessDenied or ZombieProcess exception is raised when
        retrieving that particular process information.

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
			try:
				if proc.name().lower() != name: continue
			except psutil.AccessDenied as e:
				dev_print('process_list error: ' + repr(e))
		di = proc.as_dict(attrs=ATTRS, ad_value=ad_value)
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

def process_kill(process, cmd_filter:str=None):
	''' Kills the prosess.
	'''
	if isinstance(process, int):
		try:
			psutil.Process(process).kill()
		except ProcessLookupError:
			dev_print(f'process_kill: PID {process} not found')
	elif isinstance(process, str):
		name = process.lower()
		if cmd_filter: cmd_filter = cmd_filter.lower()
		for proc in psutil.process_iter(attrs=['name']):
			if proc.name().lower() == name:
				if cmd_filter:
					if cmd_filter in ' '.join(proc.cmdline()).lower():
						proc.kill()
				else:
					proc.kill()
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

def process_close(process, timeout:int=10
, cmd_filter:str=None):
	''' Kills the process 'softly'. Returns 'True' if process
		was closed 'softly' and False if process was killed
		after timeout.
	'''
	def collect_windows(hwnd, param=None):
		nonlocal windows
		windows.append(hwnd)
		return True
	pid = process_get(process, cmd_filter)
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

def wts_user_sessionid(users, only_active:bool=True)->list:
	''' Convert list of users to list of
		session id's.
		only_active - return only WTSActive sessions.
	'''
	if isinstance(users, str):
		user_dict = {users:''}
	else:
		user_dict = {u:'' for u in users}
	for ses in win32ts.WTSEnumerateSessions():
		if only_active:
			if ses['State'] != win32ts.WTSActive: continue
		user = win32ts.WTSQuerySessionInformation(
			None, ses['SessionId'], win32ts.WTSUserName
		)
		if user in user_dict.keys():
			user_dict[user] = ses['SessionId']
	if isinstance(users, str):
		return user_dict.get(users, -1)
	else:
		return [s for s in user_dict.values() if s]

def wts_message(sessionid:int, msg:str, title:str, style:int=0
, timeout:int=0, wait:bool=False)->int:
	''' Sends message to WTS session.
		style - styles like in MessageBox (0 - MB_OK).
		timeout - timeout in seconds (0 - no timeout).
		Returns same values as the MessageBox.
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





# https://stackoverflow.com/questions/48051283/call-binary-without-elevated-privilege
ntdll = ctypes.WinDLL('ntdll')
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)

TOKEN_ADJUST_SESSIONID = 0x0100
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
LPBYTE = ctypes.POINTER(wintypes.BYTE)

class _STARTUPINFO(ctypes.Structure):
	"""https://msdn.microsoft.com/en-us/library/ms686331"""
	__slots__ = ()

	_fields_ = (('cb',			  wintypes.DWORD),
				('lpReserved',	  wintypes.LPWSTR),
				('lpDesktop',	   wintypes.LPWSTR),
				('lpTitle',		 wintypes.LPWSTR),
				('dwX',			 wintypes.DWORD),
				('dwY',			 wintypes.DWORD),
				('dwXSize',		 wintypes.DWORD),
				('dwYSize',		 wintypes.DWORD),
				('dwXCountChars',   wintypes.DWORD),
				('dwYCountChars',   wintypes.DWORD),
				('dwFillAttribute', wintypes.DWORD),
				('dwFlags',		 wintypes.DWORD),
				('wShowWindow',	 wintypes.WORD),
				('cbReserved2',	 wintypes.WORD),
				('lpReserved2',	 LPBYTE),
				('hStdInput',	   wintypes.HANDLE),
				('hStdOutput',	  wintypes.HANDLE),
				('hStdError',	   wintypes.HANDLE))

	def __init__(self, **kwds):
		self.cb = ctypes.sizeof(self)
		super(_STARTUPINFO, self).__init__(**kwds)

LPSTARTUPINFO = ctypes.POINTER(_STARTUPINFO)

class PROCESS_INFORMATION(ctypes.Structure):
	"""https://msdn.microsoft.com/en-us/library/ms684873"""
	__slots__ = ()

	_fields_ = (('hProcess',	wintypes.HANDLE),
				('hThread',	 wintypes.HANDLE),
				('dwProcessId', wintypes.DWORD),
				('dwThreadId',  wintypes.DWORD))

LPPROCESS_INFORMATION = ctypes.POINTER(PROCESS_INFORMATION)

kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

advapi32.CreateProcessWithTokenW.argtypes = (
	wintypes.HANDLE,
	wintypes.DWORD,
	wintypes.LPCWSTR,
	wintypes.LPWSTR,
	wintypes.DWORD,
	wintypes.LPCWSTR,
	wintypes.LPCWSTR,
	LPSTARTUPINFO,
	LPPROCESS_INFORMATION)

user32.GetShellWindow.restype = wintypes.HWND

def adjust_token_privileges(htoken, state):
	prev_state = win32security.AdjustTokenPrivileges(htoken, False, state)
	error = win32api.GetLastError()
	if error == winerror.ERROR_NOT_ALL_ASSIGNED:
		raise pywintypes.error(
				error, 'AdjustTokenPrivileges',
				win32api.FormatMessageW(error))
	return prev_state

def enable_token_privileges(htoken, *privilege_names):
	state = []
	for name in privilege_names:
		state.append((win32security.LookupPrivilegeValue(None, name),
					  win32con.SE_PRIVILEGE_ENABLED))
	return adjust_token_privileges(htoken, state)

@contextlib.contextmanager
def open_effective_token(access, open_as_self=True):
	hthread = win32api.GetCurrentThread()
	impersonated_self = False
	try:
		htoken = win32security.OpenThreadToken(
			hthread, access, open_as_self)
	except pywintypes.error as e:
		if e.winerror != winerror.ERROR_NO_TOKEN:
			raise
		win32security.ImpersonateSelf(win32security.SecurityImpersonation)
		impersonated_self = True
		htoken = win32security.OpenThreadToken(
			hthread, access, open_as_self)
	try:
		yield htoken
	finally:
		if impersonated_self:
			win32security.SetThreadToken(None, None)

@contextlib.contextmanager
def enable_privileges(*privilege_names):
	"""Enable a set of privileges for the current thread."""
	prev_state = ()
	with open_effective_token(
			win32con.TOKEN_QUERY |
			win32con.TOKEN_ADJUST_PRIVILEGES) as htoken:
		prev_state = enable_token_privileges(htoken, *privilege_names)
		try:
			yield
		finally:
			if prev_state:
				adjust_token_privileges(htoken, prev_state)

def duplicate_shell_token():
	hWndShell = user32.GetShellWindow()
	if not hWndShell:
		raise pywintypes.error(
				winerror.ERROR_FILE_NOT_FOUND,
				'GetShellWindow', 'no shell window')
	tid, pid = win32process.GetWindowThreadProcessId(hWndShell)
	hProcShell = win32api.OpenProcess(
					win32con.PROCESS_QUERY_INFORMATION, False, pid)
	hTokenShell = win32security.OpenProcessToken(
					hProcShell, win32con.TOKEN_DUPLICATE)
	return win32security.DuplicateTokenEx(
				hTokenShell,
				win32security.SecurityImpersonation,
				win32con.TOKEN_ASSIGN_PRIMARY |
				win32con.TOKEN_DUPLICATE |
				win32con.TOKEN_QUERY |
				win32con.TOKEN_ADJUST_DEFAULT |
				TOKEN_ADJUST_SESSIONID,
				win32security.TokenPrimary, None)

@contextlib.contextmanager
def impersonate_system():
	with enable_privileges(win32security.SE_DEBUG_NAME):
		pid_csr = ntdll.CsrGetProcessId()
		hprocess_csr = win32api.OpenProcess(
			PROCESS_QUERY_LIMITED_INFORMATION, False, pid_csr)
		htoken_csr = win32security.OpenProcessToken(
			hprocess_csr, win32con.TOKEN_DUPLICATE)
	htoken = win32security.DuplicateTokenEx(
		htoken_csr, win32security.SecurityImpersonation,
		win32con.TOKEN_QUERY |
		win32con.TOKEN_IMPERSONATE |
		win32con.TOKEN_ADJUST_PRIVILEGES,
		win32security.TokenImpersonation)
	enable_token_privileges(
		htoken,
		win32security.SE_TCB_NAME,
		win32security.SE_INCREASE_QUOTA_NAME,
		win32security.SE_ASSIGNPRIMARYTOKEN_NAME)
	try:
		htoken_prev = win32security.OpenThreadToken(
			win32api.GetCurrentThread(), win32con.TOKEN_IMPERSONATE, True)
	except pywintypes.error as e:
		if e.winerror != winerror.ERROR_NO_TOKEN:
			raise
		htoken_prev = None
	win32security.SetThreadToken(None, htoken)
	try:
		yield
	finally:
		win32security.SetThreadToken(None, htoken_prev)

def startupinfo_update(si_src, si_dst):
	for name in ('lpDesktop', 'lpTitle', 'dwX', 'dwY', 'dwXSize',
				 'dwYSize', 'dwXCountChars', 'dwYCountChars',
				 'dwFillAttribute', 'dwFlags', 'wShowWindow',
				 'hStdInput', 'hStdOutput', 'hStdError'):
		try:
			setattr(si_dst, name, getattr(si_src, name))
		except AttributeError:
			pass

def runas_session_user(cmd, executable=None, creationflags=0, cwd=None,
					   startupinfo=None, return_handles=False):
	if not creationflags & win32con.DETACHED_PROCESS:
		creationflags |= win32con.CREATE_NEW_CONSOLE
	if cwd is None:
		cwd = os.getcwd()
	si = win32process.STARTUPINFO()
	if startupinfo:
		startupinfo_update(startupinfo, si)
	with impersonate_system():
		htoken_user = win32ts.WTSQueryUserToken(
			win32ts.WTS_CURRENT_SESSION)
		hProcess, hThread, dwProcessId, dwThreadId = (
			win32process.CreateProcessAsUser(
				htoken_user, executable, cmd, None, None, False,
				creationflags, None, cwd, si))
	if return_handles:
		return hProcess, hThread
	return dwProcessId, dwThreadId

def runas_shell_user(cmd, executable=None, creationflags=0, cwd=None,
					 startupinfo=None, return_handles=False):
	if not creationflags & win32con.DETACHED_PROCESS:
		creationflags |= win32con.CREATE_NEW_CONSOLE
	if cwd is None:
		cwd = os.getcwd()
	si = _STARTUPINFO()
	if startupinfo:
		startupinfo_update(startupinfo, si)
	pi = PROCESS_INFORMATION()
	try:
		htoken = duplicate_shell_token()
	except pywintypes.error as e:
		if e.winerror != winerror.ERROR_FILE_NOT_FOUND:
			raise
		return runas_session_user(cmd, executable, creationflags, cwd,
					startupinfo, return_handles)
	with enable_privileges(win32security.SE_IMPERSONATE_NAME):
		if not advapi32.CreateProcessWithTokenW(
					int(htoken), 0, executable, cmd, creationflags, None,
					cwd, ctypes.byref(si), ctypes.byref(pi)):
			error = ctypes.get_last_error()
			raise pywintypes.error(
				error, 'CreateProcessWithTokenW',
				win32api.FormatMessageW(error))
	hProcess = pywintypes.HANDLE(pi.hProcess)
	hThread = pywintypes.HANDLE(pi.hThread)
	if return_handles:
		return hProcess, hThread
	return pi.dwProcessId, pi.dwThreadId

def runas_shell_user_wait(cmd, executable=None
, creationflags=0, cwd=None,
startupinfo=None, timeout:int=-1)->int:
	'''	runas_shell_user and get process return code
		
		timeout - how many milliseconds to wait.
		Default is -1 - return only when process is closed.

		Test (with admin rights):
			runas_shell_user_wait('ping 8.8.8.8 -n 1')
			runas_shell_user_wait('ping asdfasdfasdfasdf -n 1')
	'''
	proc_handle = runas_shell_user(
		cmd=cmd
		, executable=executable
		, creationflags=creationflags
		, cwd=cwd
		, startupinfo=startupinfo
		, return_handles=True
	)[0]
	win32event.WaitForSingleObject(
		proc_handle
		, timeout
	)
	return win32process.GetExitCodeProcess(proc_handle)


