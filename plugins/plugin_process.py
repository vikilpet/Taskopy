import subprocess
import os

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

def app_start(app_path:str, cwd:str=None, app_args:str=''
	, wait=False, shell=True, hidden=False
	, minimized=False, maximized=False):
	''' app_path - path to file or path to executable.
		app_args - command-line parameters
		cwd - working directory
		If wait - return process exit code

		https://docs.python.org/3/library/subprocess.html
	'''

	app_path = app_path.split()
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
	
def app_start_test(app_path:str, app_args:str='', wait=True, shell=True
				, hidden=False,minimized=False, maximized=False):
	''' app_path - path to file or path to executable.
		app_args - command-line parameters
		If wait - return process exit code

		https://docs.python.org/3/library/subprocess.html
	'''
	DETACHED_PROCESS = 0x00000008
	CREATE_NO_WINDOW = 0x08000000
	CREATE_NEW_CONSOLE = 0x00000010

	SW_MINIMIZE = 6
	SW_SHOWMINNOACTIVE = 7
	SW_HIDE = 0
	SW_FORCEMINIMIZE = 11

	app_path = [app_path]
	if app_args: app_path += app_args.split()

	info = subprocess.STARTUPINFO()
	info.dwFlags = subprocess.STARTF_USESHOWWINDOW
	info.wShowWindow = SW_SHOWMINNOACTIVE
	proc = subprocess.Popen(app_path
		, close_fds=True
		, creationflags=DETACHED_PROCESS
		, startupinfo=info
		, shell=shell
	)
	proc.wait()
	return proc.returncode
	
	return
	
	
	if wait:
		proc = subprocess.Popen(app_path, shell=shell, close_fds=True
			, creationflags=DETACHED_PROCESS, startupinfo=info)
		proc.wait()
		return proc.returncode
	else:
		subprocess.Popen([app_path], shell=shell)
		return True
	
