import subprocess
import os
import sys
import ctypes
import psutil
import time
from typing import Iterable
from dataclasses import dataclass
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

from .tools import DictToObj, dev_print, msgbox, tprint, patch_import
from .plugin_filesystem import path_exists, path_get
from .plugin_system import win_list_top

# https://psutil.readthedocs.io/en/latest/

_SIZE_UNITS = {'gb':1073741824, 'mb':1048576, 'kb':1024, 'b':1, 'percent':1}

def file_open(fullpath:str, parameters:str=None, operation:str='open'
, cwd:str=None, showcmd:int=win32con.SW_SHOWNORMAL):
	'''
	Opens file or URL in an associated program.  
	*parameters* - command-line parameters
	to be passed to a program.  
	*operation* - operation to perform. With executable
	use 'runas' for elevation (UAC).  
	*cwd* - change working directory.  
	*showcmd* - how window of a program should be
	displayed. From `constants`: *WIN_MINIMIZED*
	, *WIN_MAXIMIZED*, *WIN_HIDDEN*  

	'''
	win32api.ShellExecute(
		None
		, operation.lower()
		, path_get(fullpath)
		, parameters
		, cwd
		, showcmd
	)

def proc_get(process, cmd_filter:str=None)->int:
	'''
	Returns PID of process or *-1* if not found.
	
	*cmd_filter* - find process with that
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
			dev_print('proc_get error: ' + repr(e))
			continue
		if proc_name == name:
			if not cmd_filter:
				return proc.pid
			if cmd_filter in ' '.join(proc.cmdline()).lower():
				return proc.pid
	return -1

def proc_start(
	proc_path:Iterable
	, args:Iterable=()
	, wait:bool=False
	, capture:bool=False
	, encoding:str|None=None
	, shell:bool=False
	, cwd:str|None=None
	, env:dict=dict()
	, window:str=''
	, priority:str=''
	, its_script:bool=False
	, args_as_str:bool=False
)->tuple|int:
	'''
	Starts application.
	
	Returns:

		if capture - (returncode, stdout, stderr)
		if wait - return code
		otherwise - PID of a new process.
	
	proc_path - path to file or path to executable. Do not add
	double quotes.
	
	args (list or str) - command-line parameters.

	args_as_str - do not split args into list. Useful
	if application command line contains quotes. It will
	strip white space characters so you can use multiline string.

	cwd - change working directory.
	
	wait - wait for the program to complete.

	capture - capture stdout and stderr.

	env - add this environments to the process

	window - maximized(short - 'max'), minimized('min')
		or hidden('hid').

	priority - one of 'above', 'below', 'high', 'idle', 'normal'
		or 'realtime'.

	its_script - it's a script from python Scripts directory.
	Examples: 'youtube-dl.exe', 'pipreqs.exe'.

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
	if isinstance(proc_path, str):
		if its_script:
			if not proc_path.endswith('.exe'): proc_path += '.exe'
			proc_path = [
				sys.executable
				, os.path.join(
					os.path.dirname(sys.executable)
					, 'Scripts', proc_path
				)
			]
		else:
			proc_path = [proc_path]
	elif not isinstance(proc_path, (list, tuple)):
		raise Exception('Unknown type of proc_path')
	if args:
		if isinstance(args, str):
			if args_as_str:
				proc_path = proc_path[0] + ' ' \
					+ args.strip().replace('\r\n', ' ') \
						.replace('\n', ' ').replace('\t', ' ')
			else:
				proc_path += args.split()
		elif isinstance(args, (list, tuple)):
			proc_path += args
		else:
			raise Exception('Unknown type of args')
	if not args_as_str: proc_path = list( map(str, proc_path) )
	if not cwd and not args_as_str:
		if ':\\' in proc_path[0]:
			if its_script:
				cwd = os.getcwd()
			else:
				cwd = os.path.dirname(proc_path[0])
	startupinfo = subprocess.STARTUPINFO()
	creationflags = win32con.DETACHED_PROCESS
	startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
	if priority:
		creationflags |= PRIORITIES.get(
			priority.lower()
			, subprocess.NORMAL_PRIORITY_CLASS
		)
	if isinstance(window, int):
		startupinfo.wShowWindow = window
	else:
		if window is None: window = 'normal'
		window = window.lower()
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
		'args': proc_path
		, 'shell': shell
		, 'close_fds': True
		, 'cwd': cwd
		, 'creationflags': creationflags
		, 'startupinfo': startupinfo
		, 'encoding': encoding
		, 'errors': 'replace'
		, 'stdin': subprocess.PIPE
	}
	if env:
		env = {**os.environ, **env}
		proc_args['env'] = env
	if capture: wait=True
	if wait:
		proc_func = subprocess.run
		if capture:
			proc_args['capture_output'] = True
			proc_args['shell'] = False
			proc_args['text'] = True
	else:
		proc_func = subprocess.Popen
	r = proc_func(**proc_args)
	if wait:
		if capture:
			return r.returncode, r.stdout, r.stderr
		else:
			return r.returncode
	else:
		return r.pid

def proc_exists(process, cmd_filter:str=None
, user_filter:str=None)->int:
	r'''
	Returns PID if the process with the specified name exists.  
	*process* - image name or PID.  
	*cmd_filter* - optional string to search in the
	command line of the process (case-insensitive).  
	*user_filter* - only search within processes of
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
			dev_print(f'proc_exists access denied: {process}')
	return False

def proc_list(name:str='', cmd_filter:str=None
, ad_value=None)->list:
	r'''
	Returns list of DictToObj with process information.
	*name* - image name. If not specified then list all
	processes.  
	*cmd_filter* - a substring to look for in command
	line (case-insensitive).

	Note: while iterating through the process list, the
	process may cease to exist.  
	
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
				dev_print('proc_list error: ' + repr(e))
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

def proc_cpu(process, interval:float=1.0)->float:
	r'''
	Returns CPU usage of specified PID for specified interval
	of time in seconds.  
	If a process not found then returns -1:

		asrt(proc_cpu('not existing process'), -1)
		asrt(proc_cpu(0), 1, '>')
		
	'''
	if (pid := proc_get(process)) == -1: return -1
	proc = psutil.Process(pid)
	return proc.cpu_percent(interval)

def proc_uptime(process)->float:
	r'''
	Returns process running time in seconds or -1.0
	if no process is found.
	'''
	if (pid := proc_get(process)) == -1: return -1.0
	return time.time() - psutil.Process(pid).create_time()

def proc_kill(process, cmd_filter:str=''):
	r'''
	Kills the prosess.  
	*cmd_filter* is case-insensitive.  
	'''
	if isinstance(process, int):
		try:
			psutil.Process(process).kill()
		except (ProcessLookupError, psutil.NoSuchProcess):
			dev_print(f'proc_kill: PID {process} not found')
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

def free_ram(unit:str='percent')->float:
	r'''
	Returns free RAM size.  
	*unit* - 'gb', 'mb'... or 'percent'  

		asrt( benchmark(free_ram, b_iter=3), 7_000_000, "<" )

	'''
	e = _SIZE_UNITS.get(unit.lower(), 1)
	if unit == 'percent':
		return round(100 - psutil.virtual_memory()[2], 1)
	else:
		return round(psutil.virtual_memory()[4] / e, 1)

def proc_threads_num(process):
	if (pid := proc_get(process)) == -1: return -1
	return len(psutil.Process(pid=pid).threads())

def proc_close(process, timeout:int=10
, cmd_filter:str=None)->int:
	r'''
	Kills the process *softly*. Returns `True` if process
	was closed *softly* and `False` if process was killed
	after timeout.
	'''
	def collect_windows(hwnd, param=None):
		nonlocal windows
		windows.append(hwnd)
		return True
	
	if (pid := proc_get(process, cmd_filter)) == -1: return -1
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

def wts_user_sessionid(users:str|list|tuple, only_active:bool=True)->list:
	r'''
	Convert list of users to list of session id's.  
	*only_active* - return only WTSActive sessions.
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
	r'''
	Sends a message to a WTS session.  
	It is best not to put more than 50 characters
	in the *title*.  
	*style* - styles like in `MessageBox` (0 - MB_OK).  
	*timeout* - timeout in seconds (0 - no timeout).  
	Returns same values as the `MessageBox`.  
	If `wait=False` returns *32001*  
	'''
	return win32ts.WTSSendMessage(0, sessionid
	, title, msg, style, timeout, wait)
	
def wts_cur_sessionid()->int:
	'''
	Returns *SessionID* of the current process.
	'''
	return win32ts.ProcessIdToSessionId(win32api.GetCurrentProcessId())

def wts_logoff(sessionid:int, wait:bool=False)->int:
	r'''
	Logoffs session. *wait* - wait for completion.  
	If the function fails, the return value is zero.
	'''
	return win32ts.WTSLogoffSession(0, sessionid, wait)
	
def wts_proc_list(process:str=None)->list:
	'''
	Returns list of DictToObj objects with properties:
	.sessionid:int, .pid:int, .process:str (name of exe file)
	, .pysid:obj, .username:str, .cmdline:list  
	*process* - filter by process name.
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

def service_restart(service:str):
	' Restarts windows service '
	return win32serviceutil.RestartService(service)

def service_list()->list[psutil._pswindows.WindowsService]:
	'''
	Returns the list (generator) of services.  
	Object `WindowsService` methods: as_dict, binpath, description
	, display_name, name, pid, start_type, status, username.

		for s in service_list():
			if 'Microsoft' in s.description():
				print(s)

		benchmark(lambda: tuple(service_list()))

	'''
	return psutil.win_service_iter()
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

def win_by_pid(process)->tuple:
	'''
	Returns top window of a process as a tuple (hwnd:int, title:str).
	'''
	if (pid := proc_get(process)) == -1: return None, None
	win_lst = win_list_top()
	for hwnd, title in win_lst:
		if win32process.GetWindowThreadProcessId(hwnd)[1] == pid:
			return (hwnd, title)



def os_task_start(name:str)->tuple[bool, str]:
	r'''
	Starts a Windows task.  
	'''
	ret, out, err = proc_start('schtasks', f'/run /tn "{name}"'
	, capture=True, args_as_str=True)
	if ret: return False, err
	return True, out

@dataclass
class OSTask:
	folder:str=''
	hostname:str=''
	taskname:str=''
	next_run_time:str=''
	status:str=''
	logon_mode:str=''
	last_run_time:str=''
	last_result:int=0
	author:str=''
	task_to_run:str=''
	start_in:str=''
	comment:str=''

def os_task_info(name:str='')->tuple[bool, list[OSTask]|str]:
	r'''
	Returns information about Windows tasks as list
	of `OSTask` objects or (False, 'error text').  
	*name* - to get information about one particular task.  
	Tested not in all versions of Windows.  

		status, data = os_task_info(r'\Microsoft\Windows\CertificateServicesClient\UserTask')

	'''
	ret, out, err = proc_start(
		'schtasks.exe'
		, '/query /v /fo list' + (f' /tn "{name}"' if name else '')
		, capture=True, args_as_str=True
	)
	if ret: return False, err
	os_tasks = []
	fields = tuple(enumerate(f for f in OSTask.__dataclass_fields__.keys()))
	for task_sect in out.split('\n\n'):
		values = tuple(l.split(':', maxsplit=1)[1].strip()
			for l in task_sect.strip().splitlines() if ':' in l)
		if (val_len := len(values)) < 2: continue
		os_task = OSTask()
		for num, key in fields:
			if num + 1 > val_len:
				tprint(f'not enough values ({len(values)})')
				break
			setattr(os_task, key, values[num])
		os_task.last_result = int(os_task.last_result)
		os_tasks.append(os_task)
	return True, os_tasks

if __name__ != '__main__': patch_import()
