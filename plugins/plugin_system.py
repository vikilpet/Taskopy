import ctypes
import win32api
import win32gui
import win32con
import winreg
import uptime


_TIME_UNITS = {'msec':1, 'ms':1, 'sec':1000, 's':1000, 'min':60000
				,'m':60000, 'hour':3600000, 'h':3600000}

def window_get(window=None)->int:
	''' Returns hwnd. If window is not specified then
		finds foreground window.
	'''
	if isinstance(window, str):
		return win32gui.FindWindow(None, window)
	elif isinstance(window, int):
		return window
	else:
		return win32gui.GetForegroundWindow()
	
def registry_get(fullpath:str):
	''' Get value by fullpath to registry key.
		fullpath  - string like
		'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Internet Explorer\\Build'
	'''
	if fullpath[:5] != 'HKEY_': return 'wrong path'
	hive = fullpath.split('\\')[0]
	key_path = '\\'.join(fullpath.split('\\')[1:-1])
	key_name = fullpath.split('\\')[-1]
	if hive in [w for w in winreg.__dict__ if w[:5] == 'HKEY_']:
		hive = getattr(winreg, hive)
	else:
		return 'unknown hive'
	try:
		with winreg.OpenKey(hive, key_path, 0
							, winreg.KEY_READ) as reg_key:
			value, value_type = winreg.QueryValueEx(reg_key, key_name)
			return value
	except WindowsError as e:
		return f'error: {e}'

def registry_set(fullpath:str, value, value_type:str=None):
	''' Set value by fullpath to registry key.
		If value_type not specified: if type of value is int
		then store as REG_DWORD, otherwise store as REG_SZ.
		If key doesn't exist it will be created.
		fullpath  - string like
		'HKEY_CURRENT_USER\Software\Microsoft\Calc\layout'
	'''
	if fullpath[:5] != 'HKEY_': return 'wrong path'
	hive = fullpath.split('\\')[0]
	key_path = '\\'.join(fullpath.split('\\')[1:-1])
	key_name = fullpath.split('\\')[-1]
	if value_type:
		value_type = getattr(winreg, value_type)
	else:
		if isinstance(value, int):
			value_type = winreg.REG_DWORD
		else:
			value = str(value)
			value_type = winreg.REG_SZ
	if hive in [w for w in winreg.__dict__ if w[:5] == 'HKEY_']:
		hive = getattr(winreg, hive)
	else:
		return 'unknown hive'
	try:
		with winreg.OpenKey(hive, key_path, 0
							, winreg.KEY_WRITE) as reg_key:
			winreg.SetValueEx(reg_key, key_name, 0
								, value_type, value)
		return True
	except WindowsError as e:
		return f'error: {e}'

def window_title_get(window=None)->str:
	''' Gets the title of the window.
	'''
	hwnd = window_get(window)
	if hwnd:
		return win32gui.GetWindowText(hwnd)
	else:
		return 'error: not found'

def window_title_set(window=None, new_title:str='')->int:
	''' Sets window title, returns hwnd.
	'''
	hwnd = window_get(window)
	if hwnd:
		win32gui.SetWindowText(hwnd, new_title)
		return hwnd

def window_find(title:str)->list:
	''' Find window handle by Title.
		Returns list of found window handles.
	'''
	def check_title(hwnd, title:str):
		if win32gui.GetWindowText(hwnd) == title: result.append(hwnd)
	result = []
	win32gui.EnumWindows(check_title, title)
	return result

def window_activate(window=None)->int:
	''' Bring window to front, returns hwnd.
	'''
	hwnd = window_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
		win32gui.SetForegroundWindow(hwnd)
		return hwnd
	else:
		print(f'Window {window} not found')

def window_minimize(window=None)->int:
	''' Minimize window. Returns hwnd.
	'''
	hwnd = window_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
		return hwnd
	
def window_maximize(window=None)->int:
	''' Maximize window. Returns hwnd.
	'''
	hwnd = window_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
		return hwnd

def window_restore(window=None)->int:
	''' Restore window. Returns hwnd.
	'''
	hwnd = window_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
		return hwnd

def window_show(window=None)->int:
	''' Show window. Returns hwnd.
	'''
	hwnd = window_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
		return hwnd

def window_hide(window=None)->int:
	''' Hide window. Returns hwnd.
	'''
	hwnd = window_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
		return hwnd

def window_on_top(window=None, on_top:bool=True)->int:
	''' Sets the window to stay always on top.
	'''
	hwnd = window_get(window)
	if hwnd:
		try:
			win32gui.SetWindowPos(
				hwnd
				, win32con.HWND_TOPMOST if on_top else win32con.HWND_NOTOPMOST
				, 0, 0, 0, 0
				, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE
			)
		except: pass
		return hwnd

def idle_duration(unit:str='sec')->int:
	''' Returns idle time in specified units ('msec', 'sec', 'min', 'hour').
	'''
	unit_den = _TIME_UNITS.get(unit.lower(), 1000)
	millis = (int(uptime.uptime() * 1000) - win32api.GetLastInputInfo())
	return millis // unit_den

def monitor_off():
	''' Turn off the monitor
	'''
	win32gui.SendMessage(
		win32con.HWND_BROADCAST
		, win32con.WM_SYSCOMMAND
		, win32con.SC_MONITORPOWER
		, 2
	)


def window_is_visible(window=None)->bool:
	''' Is window visible?
	''' 
	hwnd = window_get(window)
	if hwnd:
		return win32gui.IsWindowVisible(hwnd) == 1
	else:
		return False
	


def _test():
	reg_key = 'HKEY_CURRENT_USER\\Software\\Microsoft\\Calc\\layout'
	input(
		reg_key + ' = ' + str(registry_get(reg_key))
		+ '\n\nPress enter to exit'
	)

if __name__ == '__main__': _test()