import subprocess
import os
import psutil
from .tools import DictToObj

# https://psutil.readthedocs.io/en/latest/

DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010

SW_MINIMIZE = 6
SW_SHOWMINNOACTIVE = 7
SW_HIDE = 0
SW_FORCEMINIMIZE = 11

_SIZE_PREFIXES = {'gb':1073741824, 'mb':1048576, 'kb':1024, 'b':1, 'percent':1}

def file_open(fullpath:str):
	''' Open file or URL in default program
	'''
	os.startfile(fullpath)

def app_start(
	app_path:str
	, app_args=None
	, cwd:str=None
	, wait:bool=False
	, shell:bool=True
	, hidden:bool=False
	, minimized:bool=False
	, maximized:bool=False
):
	''' app_path - path to file or path to executable.
		app_args (list or str) - command-line parameters.
		cwd - working directory.
		wait - wait for execution and return process exit code.

		https://docs.python.org/3/library/subprocess.html
	'''

	app_path = [app_path]
	if app_args:
		if type(app_args) is str:
			app_path += app_args.split()
		elif type(app_args) is list:
			app_path += app_args
		else:
			raise 'Unknown type of app_args'
	
	info = subprocess.STARTUPINFO()
	info.dwFlags = subprocess.STARTF_USESHOWWINDOW
	if minimized: info.wShowWindow = SW_SHOWMINNOACTIVE

	proc = subprocess.Popen(
		app_path
		, shell=shell
		, close_fds=True
		, cwd=cwd
		, creationflags=DETACHED_PROCESS
		, startupinfo=info
	)
	if wait:
		proc.wait()
		return proc.returncode
	else:
		return True





def process_exist(name:str, cmd:str=None)->bool:
	''' Returns True if the process with the specified name exists.
		name - image name.
		cmd - optional string to search in the command line of the process.
	'''
	name = name.lower()
	if cmd: cmd=cmd.lower()
	for proc in psutil.process_iter():
		if proc.name().lower() == name:
			if cmd:
				if cmd in ' '.join(proc.cmdline()):	return True
			else:
				return True
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
	''' Kill specified prosess.
		If 'process' is int: kill by pid.
		If 'process' is str: kill all processes with that name.
	'''
	if type(process) == int:
		try:
			psutil.Process(process).kill()
		except ProcessLookupError:
			print(f'PID {process}  not found')
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
	e = _SIZE_PREFIXES.get(unit.lower(), 1)
	if unit == 'percent':
		return round(100 - psutil.virtual_memory()[2], 1)
	else:
		return psutil.virtual_memory()[4] // e