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


def file_open(fullpath:str):
	''' Open file or URL in default program
	'''
	os.startfile(fullpath)

def app_start(
	app_path:str
	, app_args:str=''
	, cwd:str=None
	, wait:bool=False
	, shell:bool=True
	, hidden:bool=False
	, minimized:bool=False
	, maximized:bool=False
):
	''' app_path - path to file or path to executable
		app_args - command-line parameters
		cwd - working directory
		wait - wait for execution and return process exit code

		https://docs.python.org/3/library/subprocess.html
	'''

	app_path = [app_path]
	if app_args: app_path += app_args.split()
	
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





def process_list(name:str='')->list:
	''' Returns list of dicts with process information.
		name - image name. If not specified then list all
			processes.
	'''
	ATTRS=['pid', 'name', 'username', 'exe', 'cmdline']

	name = name.lower()
	proc_list = []
	for proc in psutil.process_iter():
		if name:
			if proc.name().lower() == name:
				proc_list.append( DictToObj(proc.as_dict(attrs=ATTRS) ) )
		else:
			proc_list.append( DictToObj(proc.as_dict(attrs=ATTRS) ) )
	return proc_list

def process_cpu(pid:int, interval:int=1)->float:
	''' Returns CPU usage of specified PID for specified interval
		of time in seconds.
	'''
	proc = psutil.Process(pid)
	return proc.cpu_percent(interval)

def process_kill(process):
	''' Kill specified prosess.
		If process is int: kill by pid
		If process is str: kill all processes with that name.
	'''
	if type(process) == int:
		psutil.Process(process).kill()
	elif type(process) == str:
		name = process.lower()
		for proc in psutil.process_iter(attrs=['name']):
			if proc.name().lower() == name:
				proc.kill()
	else:
		raise ValueError(
			f'Unknown type of process parameter: {type(process)}'
		)
	