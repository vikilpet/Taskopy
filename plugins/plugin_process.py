import subprocess
import os
import ctypes
from ctypes import wintypes
import psutil
import time
from typing import Iterable
import functools
from dataclasses import dataclass
import win32gui
import win32api
import win32con
import win32com
import win32event
import win32process
import win32pipe
import win32file
import win32security
import win32ts
import win32serviceutil
import pythoncom
import contextlib
import winerror
import pywintypes
from .tools import dev_print, tprint, patch_import \
, thread_start, _SIZE_UNITS, winapi, cache, is_con, is_dev
from .plugin_filesystem import path_get
from .plugin_system import win_list_top, win_get

IS_64BIT = ctypes.sizeof(ctypes.c_void_p) == 8
_EPOCH_DIFF = 11_644_473_600
_EXE_PATH_BUF = 32768  # Windows MAX_LONG_PATH
_TerminateProcess = winapi.kernel32.TerminateProcess
_TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
_TerminateProcess.restype  = wintypes.BOOL
_EnumProcesses = winapi.psapi.EnumProcesses
_EnumProcesses.argtypes = [
	wintypes.LPVOID,            # lpidProcess
	wintypes.DWORD,             # cb
	ctypes.POINTER(wintypes.DWORD),    # lpcbNeeded
]
_EnumProcesses.restype = wintypes.BOOL
_ProcessIdToSessionId = winapi.kernel32.ProcessIdToSessionId
_ProcessIdToSessionId.argtypes = [
	wintypes.DWORD,            # dwProcessId
	ctypes.POINTER(wintypes.DWORD),   # pSessionId
]
_ProcessIdToSessionId.restype = wintypes.BOOL
_CommandLineToArgvW = winapi.shell32.CommandLineToArgvW
_CommandLineToArgvW.argtypes = [
	wintypes.LPCWSTR,          # lpCmdLine
	ctypes.POINTER(wintypes.INT),     # pNumArgs
]
_CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
_LocalFree = winapi.kernel32.LocalFree
_LocalFree.argtypes = [wintypes.HLOCAL]
_LocalFree.restype  = wintypes.HLOCAL
_GetProcessTimes = winapi.kernel32.GetProcessTimes
_GetProcessTimes.argtypes = [
	wintypes.HANDLE,
	ctypes.POINTER(wintypes.FILETIME),  # lpCreationTime
	ctypes.POINTER(wintypes.FILETIME),  # lpExitTime
	ctypes.POINTER(wintypes.FILETIME),  # lpKernelTime
	ctypes.POINTER(wintypes.FILETIME),  # lpUserTime
]
_GetProcessTimes.restype = wintypes.BOOL
_GetSystemTimes = winapi.kernel32.GetSystemTimes
_GetSystemTimes.argtypes = [
	ctypes.POINTER(wintypes.FILETIME),  # lpIdleTime
	ctypes.POINTER(wintypes.FILETIME),  # lpKernelTime
	ctypes.POINTER(wintypes.FILETIME),  # lpUserTime
]
_GetSystemTimes.restype = wintypes.BOOL

def file_open(fullpath, parameters:str=None, operation:str='open'
, cwd:str='', showcmd:int=win32con.SW_SHOWNORMAL):
	r'''
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
		, path_get(cwd) if cwd else None
		, showcmd
	)

def _enumerate_all_pids():
	r'''
	Yield all PIDs on the system using EnumProcesses.
	Returns 0 (System Idle) as the first entry — skip it if unwanted.
	'''
	size = 1024  # initial buffer in DWORDs (4096 bytes)
	while True:
		buf = (wintypes.DWORD * size)()
		needed = wintypes.DWORD(0)
		if not _EnumProcesses(buf, ctypes.sizeof(buf), ctypes.byref(needed)):
			return
		count = needed.value // ctypes.sizeof(wintypes.DWORD)
		if count < size:
			for i in range(count):
				yield buf[i]
			return
		size *= 2

def _pids_by_name(name_lower):
	r'''
	Yield every PID whose image name matches *name_lower*
	(case-insensitive, already pre-lowered by caller).
	'''
	snapshot = winapi.kernel32.CreateToolhelp32Snapshot(
		winapi.TH32CS_SNAPPROCESS, 0)
	if not snapshot or snapshot == winapi.INVALID_HANDLE_VALUE:
		err = ctypes.get_last_error()
		raise OSError(f'CreateToolhelp32Snapshot failed: {winapi.get_last_error()}')
	try:
		entry = winapi.PROCESSENTRY32W()
		entry.dwSize = ctypes.sizeof(winapi.PROCESSENTRY32W)
		if not winapi.kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
			err = ctypes.get_last_error()
			raise OSError(
				f'Process32FirstW failed: {winapi.get_last_error()}\n'
				f'  sizeof(PROCESSENTRY32W) = {entry.dwSize} '
				f'(expected 568 on x64, 556 on x86)'
			)
		while True:
			if entry.szExeFile.lower() == name_lower:
				yield entry.th32ProcessID
			if not winapi.kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
				break
	finally:
		winapi.kernel32.CloseHandle(snapshot)

def _read_cmdline(handle):
	r'''
	Read the command line of the process behind *handle*
	by walking its PEB via ReadProcessMemory.
	Returns the string, or None on any failure.
	'''
	bytes_read = ctypes.c_size_t()

	if IS_64BIT:
		wow64 = ctypes.c_uint64()
		if winapi.ntdll.NtQueryInformationProcess(
			handle, winapi.PROCESSWOW64_CLASS, ctypes.byref(wow64),
			ctypes.sizeof(wow64), None
		) == 0 and wow64.value:
			ptr_size  = 4
			peb_addr  = wow64.value
			pp_offset = winapi.PEB_PROCESS_PARAMETERS_OFFSET_32
			cl_offset = winapi.PEB_COMMANDLINE_OFFSET_32
		else:
			pbi = winapi.PROCESS_BASIC_INFORMATION64()
			if winapi.ntdll.NtQueryInformationProcess(
				handle, winapi.PROCESSBASICINFO_CLASS, ctypes.byref(pbi),
				ctypes.sizeof(pbi), None
			) != 0 or not pbi.PebBaseAddress:
				return None
			ptr_size  = 8
			peb_addr  = pbi.PebBaseAddress
			pp_offset = winapi.PEB_PROCESS_PARAMETERS_OFFSET_64
			cl_offset = winapi.PEB_COMMANDLINE_OFFSET_64
	else:
		pbi = winapi.PROCESS_BASIC_INFORMATION32()
		if winapi.ntdll.NtQueryInformationProcess(
			handle, winapi.PROCESSBASICINFO_CLASS, ctypes.byref(pbi),
			ctypes.sizeof(pbi), None
		) != 0 or not pbi.PebBaseAddress:
			return None
		ptr_size  = 4
		peb_addr  = pbi.PebBaseAddress
		pp_offset = winapi.PEB_PROCESS_PARAMETERS_OFFSET_32
		cl_offset = winapi.PEB_COMMANDLINE_OFFSET_32
	if ptr_size == 4:
		param_ptr = ctypes.c_uint32()
	else:
		param_ptr = ctypes.c_uint64()
	if not winapi.kernel32.ReadProcessMemory(
		handle, ctypes.c_void_p(peb_addr + pp_offset),
		ctypes.byref(param_ptr), ptr_size, ctypes.byref(bytes_read),
	):
		return None
	params = param_ptr.value
	if not params:
		return None
	if ptr_size == 4:
		unicode_str = winapi.UNICODE_STRING32()
	else:
		unicode_str = winapi.UNICODE_STRING64()
	if not winapi.kernel32.ReadProcessMemory(
		handle, ctypes.c_void_p(params + cl_offset),
		ctypes.byref(unicode_str), ctypes.sizeof(unicode_str),
		ctypes.byref(bytes_read),
	):
		return None
	if not unicode_str.Length or not unicode_str.Buffer:
		return None
	buf = ctypes.create_unicode_buffer(unicode_str.Length // 2 + 1)
	if not winapi.kernel32.ReadProcessMemory(
		handle, ctypes.c_void_p(unicode_str.Buffer),
		buf, unicode_str.Length, ctypes.byref(bytes_read),
	):
		return None
	return buf.value


def _read_user(handle):
	r"""
	Return 'DOMAIN\\User' for the process behind *handle*,
	or None if the token cannot be opened.
	"""
	try:
		token = win32security.OpenProcessToken(handle, winapi.TOKEN_QUERY)
		sid, _ = win32security.GetTokenInformation(token, win32security.TokenUser)
		user, domain, _ = win32security.LookupAccountSid(None, sid)
		return f'{domain}\\{user}'
	except Exception:
		return None

def _read_session_id(pid: int) -> int:
	r'''
	Return the Terminal Services session ID for *pid*, or -1 on failure.
	'''
	sid = wintypes.DWORD(0)
	if _ProcessIdToSessionId(pid, ctypes.byref(sid)):
		return sid.value
	return -1

def _read_creation_time(handle) -> float:
	r"""
	Return the creation time of the process behind *handle*
	as a Unix epoch timestamp (seconds since 1970-01-01),
	or 0 on failure.
	"""
	creation  = wintypes.FILETIME()
	exit_time  = wintypes.FILETIME()
	kernel    = wintypes.FILETIME()
	user_time = wintypes.FILETIME()

	ok = winapi.kernel32.GetProcessTimes(
		handle,
		ctypes.byref(creation),
		ctypes.byref(exit_time),
		ctypes.byref(kernel),
		ctypes.byref(user_time),
	)
	if not ok:
		return 0
	ft = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
	if ft == 0:
		return 0
	return ft / 10_000_000 - _EPOCH_DIFF

def _read_exe_path(handle) -> str:
	r"""
	Return the full Win32 path (e.g. 'C:\Windows\System32\cmd.exe')
	for the process behind *handle*, or '' on failure.
	"""
	buf = ctypes.create_unicode_buffer(_EXE_PATH_BUF)
	size = wintypes.DWORD(_EXE_PATH_BUF)
	ok = winapi.kernel32.QueryFullProcessImageNameW(handle, 0, buf
	, ctypes.byref(size))
	if not ok:
		return ''
	return buf.value

def _split_cmdline(cmdline: str) -> list[str]:
	r"""
	Split a Windows command line string into a list of tokens,
	using the native CommandLineToArgvW parser.
	
	'\"C:\\Python313\\python.exe\" script.py --flag'
	  → ['C:\\Python313\\python.exe', 'script.py', '--flag']
	"""
	if not cmdline:
		return []
	argc = wintypes.INT(0)
	argv = _CommandLineToArgvW(cmdline, ctypes.byref(argc))
	if not argv:
		return []
	try:
		return [argv[i] for i in range(argc.value)]
	finally:
		_LocalFree(argv)

def _ft_to_int(ft: wintypes.FILETIME) -> int:
	''' Combine FILETIME's two DWORDs into one 64-bit value (100-ns ticks). '''
	return ft.dwLowDateTime | (ft.dwHighDateTime << 32)

def _read_proc_cpu_time(handle) -> int:
	''' Total CPU time (kernel + user) for the process in 100-ns ticks. '''
	c, e, k, u = (wintypes.FILETIME() for _ in range(4))
	if _GetProcessTimes(handle, c, e, k, u):
		return _ft_to_int(k) + _ft_to_int(u)
	return -1

def _read_sys_cpu_time() -> tuple[int, int, int]:
	'''
	Returns (idle, kernel, user) total system times in 100-ns ticks.
	Each is -1 on failure.
	'''
	idle, k, u = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
	if _GetSystemTimes(idle, k, u):
		return _ft_to_int(idle), _ft_to_int(k), _ft_to_int(u)
	return -1, -1, -1

def proc_get(process, cmd_filter:str = '', user_filter:str = '')->int|None:
	r'''
	Returns PID if the process with the specified name exists or None  
	*process* - image name or PID.  
	*cmd_filter* - optional string to search in the
	command line of the process (case-insensitive).  
	*user_filter* - only search within processes of
	specified user.  
	Filtering using string filters is expensive;
	use PID whenever possible:
		asrt( bmark(proc_get, ('_',), b_iter=3), 80_000_000 )
		asrt( bmark(proc_get, (1,)), 700 )
		asrt( bmark(proc_get, ('\\taskopy.py',), b_iter=3), 70_000_000 )
		pid, user = os.getpid(), os.getlogin()
		asrt( bmark(proc_get, ('', user), b_iter=3), 80_000_000 )
		asrt( proc_get(pid, '\\taskopy.py'), pid)
		asrt( proc_get(pid, '\\python.exe', user), pid)

	'''
	if isinstance(process, int): return process
	name_lower = process.lower()
	if cmd_filter:
		cmd_filter = cmd_filter.lower()
	if user_filter:
		user_filter = user_filter.lower()
	need_cmd  = bool(cmd_filter)
	need_user = bool(user_filter)
	for pid in _pids_by_name(name_lower):
		if not need_cmd and not need_user:
			return pid

		access = winapi.PROCESS_QUERY_LIMITED_INFORMATION
		if need_cmd:
			access |= winapi.PROCESS_VM_READ

		handle = winapi.kernel32.OpenProcess(access, False, pid)
		if not handle:
			continue
		try:
			if need_cmd:
				cmdline = _read_cmdline(handle)
				if not cmdline or cmd_filter not in cmdline.lower():
					continue

			if need_user:
				usr = _read_user(handle)
				if not usr or usr.lower() != user_filter:
					continue

			return pid
		finally:
			winapi.kernel32.CloseHandle(handle)

	return None

def _create_pipe():
	sa = pywintypes.SECURITY_ATTRIBUTES()
	sa.bInheritHandle = True
	read_handle, write_handle = win32pipe.CreatePipe(sa, 0)
	win32api.SetHandleInformation(read_handle, win32con.HANDLE_FLAG_INHERIT, 0)
	return read_handle, write_handle
	
def _reader_thread(pipe, buffer_list):
	while True:
		try:
			rc, chunk = win32file.ReadFile(pipe, 4096)
			if rc == 0 and chunk:
				buffer_list.append(chunk)
			else:
				break
		except pywintypes.error as e:
			if e.winerror == 109 or e.winerror == 6:
				break
			else:
				raise

def proc_wait(
	cmd:str
	, priority=win32process.NORMAL_PRIORITY_CLASS
	, cwd=None
	, env:dict|None=None
	, make_stdin:bool=True
	, encoding:str='utf-8'
	, encoding_errors:str='replace'
	, create_console:bool=True
)->tuple[int, str, str]:
	r'''
	Start the process and wait for it to complete.  
	Returns k(return code, stdout, stderr)  
	*cmd* - command line with the program and its arguments  
	*cwd* - current working directory  
	*create_console* - to catch output of some programs  
	*env* - add this variables to the environment (not replace all)  
	'''
	stdout_read, stdout_write = _create_pipe()
	stderr_read, stderr_write = _create_pipe()
	stdin_handle = None
	if make_stdin:
		stdin_handle = win32file.CreateFile(
			'NUL',
			win32con.GENERIC_READ,
			win32con.FILE_SHARE_READ,
			None,
			win32con.OPEN_EXISTING,
			0,
			None
		)
	startup = win32process.STARTUPINFO()
	startup.dwFlags |= win32con.STARTF_USESTDHANDLES
	startup.hStdOutput = stdout_write
	startup.hStdError = stderr_write
	if make_stdin: startup.hStdInput = stdin_handle
	startup.dwFlags |= win32con.STARTF_USESHOWWINDOW
	startup.wShowWindow = win32con.SW_HIDE
	win_flag = win32con.CREATE_NEW_CONSOLE if create_console \
		else win32con.CREATE_NO_WINDOW
	creation_flags = win_flag | priority
	if env: env = {**os.environ, **env}
	proc_handle, thread_handle, proc_id, thread_id = win32process.CreateProcess(
		None,
		cmd,
		None,
		None,
		True,
		creation_flags,
		env,
		cwd,
		startup
	)
	win32file.CloseHandle(stdout_write)
	win32file.CloseHandle(stderr_write)
	if stdin_handle: win32file.CloseHandle(stdin_handle)
	stdout_chunks = []
	stderr_chunks = []
	thread_out = thread_start(_reader_thread, args=(stdout_read, stdout_chunks)
	, ident='proc_wait out: ' + cmd)
	thread_err = thread_start(_reader_thread, args=(stderr_read, stderr_chunks)
	, ident='proc_wait err: ' + cmd)
	win32event.WaitForSingleObject(proc_handle, win32event.INFINITE)
	exit_code = win32process.GetExitCodeProcess(proc_handle)
	win32api.CloseHandle(proc_handle)
	win32api.CloseHandle(thread_handle)
	thread_out.join()
	thread_err.join()
	win32file.CloseHandle(stdout_read)
	win32file.CloseHandle(stderr_read)
	stdout_data = b''.join(stdout_chunks)
	stderr_data = b''.join(stderr_chunks)
	return (
		exit_code
		, stdout_data.decode(encoding=encoding, errors=encoding_errors)
		, stderr_data.decode(encoding=encoding, errors=encoding_errors)
	)

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
	, args_as_str:bool=False
)->tuple|int:
	r'''
	Launches the application.  
	Returns:

		if capture - (returncode, stdout, stderr)
		if wait - return code
		otherwise - PID of a new process.
	
	*proc_path* - path to file or path to executable. Do not add
	double quotes.  
	*args:list|str* - command-line parameters.  
	*args_as_str* - do not split args into list. Useful
	if program command line contains quotes. It will
	strip white space characters so you can use multiline string.  
	*cwd* - change working directory.  
	*wait* - wait for the program to complete.  
	*capture* - capture stdout and stderr.  
	*env - add this environments to the process.  
	*window* - maximized(short - 'max'), minimized('min') or hidden('hid').  
	*priority* - one of 'above', 'below', 'high', 'idle', 'normal'
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
	if isinstance(proc_path, str):
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

def proc_owner(process)->str:
	r'''
	Gets the owner of a PID.

		user = os.getlogin()
		pid = proc_get('explorer.exe')
		asrt( proc_owner(pid), user)
		asrt( bmark(proc_owner, (pid,)), 200_000 )

	'''
	if (pid := proc_get(process)) == None: return ''
	try:
		handle = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION
		, False, pid)
		try:
			token = win32security.OpenProcessToken(handle, win32con.TOKEN_QUERY)
			try:
				sid, _ = win32security.GetTokenInformation(token, win32security.TokenUser)
				user, _, _ = win32security.LookupAccountSid(None, sid)
				return user
			finally:
				token.Close()
		finally:
			win32api.CloseHandle(handle)
	except Exception:
		return ''


def proc_exists(pid:int)->bool:
	r'''
	Returns True if the PID exists.  

		pid = proc_get('explorer.exe')
		asrt(proc_exists(pid), True)
		asrt( bmark(proc_exists, (pid,)), 7_100 )

	'''
	try:
		h_process = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION
		, False, pid)
		win32api.CloseHandle(h_process)
		return True
	except win32api.error:
		return False


@dataclass
class Process:
	pid: int
	strip_pc: bool = True
	_exe_path: str = ''   # full exe path (pre-read, NOT a basename)
	_cmdline: str = ''    # pre-read cmdline
	_user: str = ''       # pre-read raw 'DOMAIN\User'

	def _safe_handle(self, access:int, fn, default=None):
		'''Open a process handle, call *fn(handle)*, auto-close.'''
		handle = winapi.kernel32.OpenProcess(access, False, self.pid)
		if not handle:
			return default
		try:
			return fn(handle)
		except Exception:
			return default
		finally:
			winapi.kernel32.CloseHandle(handle)

	@functools.cached_property
	def cmdline(self) -> str:
		''' Command line as a string '''
		if self._cmdline:
			return self._cmdline
		access = win32con.PROCESS_QUERY_LIMITED_INFORMATION \
		         | win32con.PROCESS_VM_READ
		return self._safe_handle(access, _read_cmdline, default='')

	@functools.cached_property
	def cmdline_list(self) -> list[str]:
		''' Command line as a list '''
		return self.cmdline.split() if self.cmdline else []

	@functools.cached_property
	def username(self) -> str:
		if self._user:
			return self._user
		usr = self._safe_handle(
			win32con.PROCESS_QUERY_LIMITED_INFORMATION,
			_read_user,
			default=''
		)
		if usr and self.strip_pc and '\\' in usr:
			usr = usr.split('\\', 1)[1]
		return usr

	@functools.cached_property
	def fullpath(self) -> str:
		''' Full path to the exe file '''
		if self._exe_path:
			return self._exe_path
		return self._safe_handle(
			win32con.PROCESS_QUERY_LIMITED_INFORMATION,
			_read_exe_path,
			default=''
		)

	@functools.cached_property
	def name(self) -> str:
		''' Process exe file name (not a full path) '''
		path = self.fullpath
		return os.path.basename(path) if path else ''

	def uptime(self) -> float:
		''' Uptime in seconds (not cached — changes over time) '''
		ctime = self._safe_handle(
			win32con.PROCESS_QUERY_LIMITED_INFORMATION,
			_read_creation_time,
			default=0
		)
		return time.time() - ctime if ctime else 0

	def kill(self, exit_code: int = 1):
		r'''
		Kill the current process.
		Raises OSError if the process cannot be opened or terminated.
		'''
		handle = winapi.kernel32.OpenProcess(
			win32con.PROCESS_TERMINATE, False, self.pid
		)
		if not handle:
			err = ctypes.get_last_error()
			raise OSError(
				f'OpenProcess({self.pid}) for TERMINATE failed: error {err}'
			)
		try:
			if not _TerminateProcess(handle, exit_code):
				err = ctypes.get_last_error()
				raise OSError(
					f'TerminateProcess({self.pid}) failed: error {err}'
				)
		finally:
			winapi.kernel32.CloseHandle(handle)

	@functools.cached_property
	def sessionid(self) -> int:
		''' Terminal Services session ID (0 = Services, 1 = Console, etc.) '''
		return _read_session_id(self.pid)

	@functools.cached_property
	def argv(self) -> list[str]:
		r"""
		Command line split into tokens.
		argv[0] is the exe path (as it was on launch, possibly quoted).
		"""
		cmd = self.cmdline   # raw string from PEB (already cached)
		if not cmd:
			return []
		return _split_cmdline(cmd)

	@functools.cached_property
	def args(self) -> str:
		r"""
		Command line arguments **without** the exe path.
		
		argv = ['C:\\Python313\\python.exe', 'script.py', '--flag']
		args = 'script.py --flag'
		"""
		av = self.argv
		return ' '.join(av[1:]) if len(av) > 1 else ''

	def cpu_percent(self, interval: float = 1.0) -> float:
		r'''
		Returns CPU usage percentage over *interval* seconds.
		100% means one core is fully utilized.
		Returns -1.0 if the process cannot be opened or is dead.
		
		Special case: PID 0 (System Idle) uses idle time from GetSystemTimes.
		'''
		if self.pid == 0:
			i1, k1, u1 = _read_sys_cpu_time()
			if i1 == -1:
				return -1.0
			time.sleep(interval)
			i2, k2, u2 = _read_sys_cpu_time()
			if i2 == -1:
				return -1.0
			sys_delta = (k2 + u2) - (k1 + u1)
			if sys_delta == 0:
				return 0.0
			idle_delta = i2 - i1
			return (idle_delta / sys_delta) * 100.0

		handle = winapi.kernel32.OpenProcess(
			winapi.PROCESS_QUERY_LIMITED_INFORMATION, False, self.pid
		)
		if not handle:
			return -1.0
		try:
			t1 = _read_proc_cpu_time(handle)
			_, k1, u1 = _read_sys_cpu_time()
			if t1 == -1:
				return -1.0
			time.sleep(interval)
			t2 = _read_proc_cpu_time(handle)
			_, k2, u2 = _read_sys_cpu_time()
			if t2 == -1:
				return -1.0

			proc_delta = t2 - t1
			sys_delta = (k2 + u2) - (k1 + u1)

			if sys_delta == 0:
				return 0.0
			return (proc_delta / sys_delta) * 100.0
		finally:
			winapi.kernel32.CloseHandle(handle)


def proc_list(name:str='', cmd_filter:str='', user_filter:str=''
, strip_pc:bool=True)->list[Process]:
	r'''
	Returns list of `Process` objects.  
	*name* - image name (case-insensitive). If not specified then list all
	processes.  
	*cmd_filter* - a substring to look for in command line (case-insensitive).  
	*user_filter* - only search within processes of specified user.  

		asrt( bmark( lambda: len(proc_list()), b_iter=1), 90_000_000 )
		table = [('Name', 'PID', 'User', 'Uptime', 'CPU', 'CMDline')]
		for proc in proc_list('')[:10]:
			table.append((proc.name, proc.pid, proc.username
			, int(proc.uptime()), proc.cpu_percent(.1), proc.cmdline))
		table_print(table, use_headers=True)


	'''
	result:list[Process] = []
	name_lower = name.lower() if name else ''
	if cmd_filter:
		cmd_filter = cmd_filter.lower()
	if user_filter:
		user_filter = user_filter.lower()
	need_name = bool(name_lower)
	need_cmd  = bool(cmd_filter)
	need_user = bool(user_filter)
	if name_lower:
		pids = _pids_by_name(name_lower)
	else:
		pids = _enumerate_all_pids()

	for pid in pids:
		if pid == 0:
			continue  # System Idle Process, skip

		access = winapi.PROCESS_QUERY_LIMITED_INFORMATION
		if need_cmd:
			access |= winapi.PROCESS_VM_READ

		handle = winapi.kernel32.OpenProcess(access, False, pid)
		if not handle:
			continue
		try:
			exe_path = _read_exe_path(handle)
			if not exe_path:
				continue
			if need_name:
				actual_name = os.path.basename(exe_path).lower()
				if actual_name != name_lower:
					continue
			pre_cmd  = ''
			pre_user = ''
			if need_cmd:
				cmdline = _read_cmdline(handle)
				if not cmdline or cmd_filter not in cmdline.lower():
					continue
				pre_cmd = cmdline
			if need_user:
				usr = _read_user(handle)
				if not usr:
					continue
				if usr.lower() != user_filter:
					continue
				pre_user = usr

			result.append(Process(
				pid=pid,
				strip_pc=strip_pc,
				_exe_path=exe_path,
				_cmdline=pre_cmd,
				_user=pre_user,
			))
		finally:
			winapi.kernel32.CloseHandle(handle)

	return result

def proc_cpu(process, interval:float=1.0)->float:
	r'''
	Returns CPU usage of specified PID for specified interval
	of time in seconds.
	If a process not found then returns -1.
	'''
	if (pid := proc_get(process)) is None:
		return -1
	proc = Process(pid=pid)
	return proc.cpu_percent(interval)

def proc_uptime(process)->float:
	r'''
	Returns process running time in seconds or -1.0
	if no process is found.
	'''
	if (pid := proc_get(process)) is None: return -1
	return Process(pid=pid).uptime()

def proc_kill(pid:int):
	r'''
	Kills the prosess.  
	*cmd_filter* is case-insensitive.  
	'''
	Process(pid=pid).kill()

def free_ram(unit:str='percent')->float:
	r'''
	Returns free RAM size.  
	*unit* - 'gb', 'mb'... or 'percent'  

		asrt( bmark(free_ram, b_iter=3), 70_000_000 )

	'''
	if unit == 'percent':
		return round(100 - psutil.virtual_memory()[2], 1)
	else:
		e = _SIZE_UNITS.get(unit.lower(), 1)
		return round(psutil.virtual_memory()[4] / e, 1)

def proc_thread_num(process)->int:
	if (pid := proc_get(process)) == None: return -1
	return len(psutil.Process(pid=pid).threads())

def proc_handle_num(process)->int:
	if (pid := proc_get(process)) == None: return -1
	return psutil.Process(pid=pid).num_handles()

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
	
	if (pid := proc_get(process, cmd_filter)) == None: return -1
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
			pass
	for _ in range(timeout):
		time.sleep(1)
		if not psutil.pid_exists(pid): return True
	try:
		psutil.Process(pid).kill()
	except ProcessLookupError:
		dev_print(f'PID {pid} was not found')
	return False

def proc_fpath(process)->str:
	r'''
	Retrieves the full path of the process  

		asrt( bmark(proc_fpath, (17532,)), 5_000 )
		
	'''
	if (pid := proc_get(process)) == None: return ''
	hProc = winapi.kernel32.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION
	, False, pid)
	if not hProc: return ''
	try:
		size = wintypes.DWORD(260)  # MAX_PATH
		buf = ctypes.create_unicode_buffer(size.value)
		ok = winapi.kernel32.QueryFullProcessImageNameW(hProc, 0, buf
		, ctypes.byref(size))
		return buf.value if ok else ''
	finally:
		winapi.kernel32.CloseHandle(hProc)

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

		bmark(lambda: tuple(service_list()))

	'''
	return psutil.win_service_iter()

def is_admin()->bool:
	r'''
	Checks if Taskopy is running with elevated privileges

		asrt( bmark(is_admin), 18_000 )
	
	'''
	return win32com.shell.shell.IsUserAnAdmin()
# https://stackoverflow.com/questions/48051283/call-binary-without-elevated-privilege
winapi.kernel32.OpenProcess.argtypes = (
	wintypes.DWORD,  # dwDesiredAccess
	wintypes.BOOL,   # bInheritHandle
	wintypes.DWORD   # dwProcessId
)
winapi.kernel32.OpenProcess.restype = wintypes.HANDLE
winapi.kernel32.QueryFullProcessImageNameW.argtypes = (
	wintypes.HANDLE,       # hProcess
	wintypes.DWORD,        # dwFlags (0)
	wintypes.LPWSTR,       # lpExeName
	ctypes.POINTER(wintypes.DWORD)  # lpdwSize
)
winapi.kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
winapi.kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

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
winapi.advapi32.CreateProcessWithTokenW.argtypes = (
	wintypes.HANDLE,
	wintypes.DWORD,
	wintypes.LPCWSTR,
	wintypes.LPWSTR,
	wintypes.DWORD,
	wintypes.LPCWSTR,
	wintypes.LPCWSTR,
	LPSTARTUPINFO,
	LPPROCESS_INFORMATION)
winapi.user32.GetShellWindow.restype = wintypes.HWND

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
	hWndShell = winapi.user32.GetShellWindow()
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
		pid_csr = winapi.ntdll.CsrGetProcessId()
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
		if not winapi.advapi32.CreateProcessWithTokenW(
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
	r'''
	Returns top window of a process as a tuple (hwnd:int, title:str).
	'''
	if (pid := proc_get(process)) == None: return None, None
	win_lst = win_list_top()
	for hwnd, title in win_lst:
		if win32process.GetWindowThreadProcessId(hwnd)[1] == pid:
			return (hwnd, title)
	else:
		return ()

def proc_fpath_by_win(window)->str:
	r'''
	Finds the process full path by window.  

		asrt( proc_fpath_by_win('Taskopy').endswith('py.exe'), True )
		asrt( bmark(proc_fpath_by_win, ('Taskopy*',)), 4_500_000 )

	'''
	if not (hwnd := win_get(window) ): return ''
	pid = win32process.GetWindowThreadProcessId(hwnd)[1]
	if not pid: return ''
	return proc_fpath(pid)

def proc_cmdline(process, full:bool=False)->str:
	r'''
	Returns a command line.  
	*full* - include process path.  
	'''
	if (pid := proc_get(process)) is None:
		return ''
	proc = Process(pid=pid)
	if full:
		return proc.cmdline
	return proc.args



def os_task_start(name:str)->tuple[bool, str]:
	r'''
	Starts a Windows task.  
	'''
	ret, out, err = proc_wait(f'schtasks /run /tn "{name}"')
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
	Not tested in all versions of Windows.  

		status, data = os_task_info(r'\Microsoft\Windows\CertificateServicesClient\UserTask')

	'''
	ret, out, err = proc_wait(
		'schtasks.exe /query /v /fo list'
		+ (f' /tn "{name}"' if name else '')
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
