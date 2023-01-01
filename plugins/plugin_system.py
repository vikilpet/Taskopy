import ctypes
import win32api
import win32gui
import win32con
import winreg
import pywintypes
import uptime
from time import sleep
import ctypes
from .tools import *
try:
	import constants as tcon
except ModuleNotFoundError:
	import plugins.constants as tcon
LockWorkStation = ctypes.windll.user32.LockWorkStation
_GetAncestor = ctypes.windll.user32.GetAncestor
_SendNotifyMessage = ctypes.windll.user32.SendNotifyMessageA
_WM_APPCOMMAND = 0x319
_APPCOMMAND_VOLUME_MUTE = 0x80000
_APPCOMMAND_VOLUME_DOWN = 0x90000
_APPCOMMAND_VOLUME_UP = 0xA0000

def win_get(window=None, class_name:str=None)->int:
	'''
	Returns window handle. If window is not specified then
	finds foreground window.
	You can use asterisk for imprecise search:

		tass( win_get('Total Commander*'), 0, '>' )
		tass( win_get('Non-existent window'), 0 )

	'''
	if isinstance(window, int):
		return window
	elif isinstance(window, str):
		if '*' in window:
			if not (li := win_find(title=window.strip('*'), exact=False) ):
				return 0
			return li[0]
		else:
			return win32gui.FindWindow(class_name, window)
	elif not window and class_name:
		return win32gui.FindWindow(class_name, window)
	else:
		return win32gui.GetForegroundWindow()
	
def registry_get(fullpath:str):
	''' Get value by fullpath to registry key.
		fullpath - full path to key.
		Example:
		
			>registry_get('HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Internet Explorer\\Build')
			'99600'
	'''
	if fullpath[:5] != 'HKEY_':
		return Exception('Path must begin with with «HKEY_»')
	hive = fullpath.split('\\')[0]
	key_path = '\\'.join(fullpath.split('\\')[1:-1])
	key_name = fullpath.split('\\')[-1]
	if hive in [w for w in winreg.__dict__ if w[:5] == 'HKEY_']:
		hive = getattr(winreg, hive)
	else:
		return Exception('unknown hive')
	try:
		with winreg.OpenKey(hive, key_path, 0
		, winreg.KEY_READ) as reg_key:
			value, value_type = winreg.QueryValueEx(reg_key, key_name)
		return value
	except WindowsError as e:
		tdebug(e)
		return e

def registry_set(fullpath:str, value, value_type:str=None):
	r''' Set value by fullpath to registry key.
		If value_type not specified: if type of value is int
		then store as REG_DWORD, otherwise store as REG_SZ.
		If key doesn't exist it will be created.
		fullpath  - string like
		'HKEY_CURRENT_USER\Software\Microsoft\Calc\layout'
	'''
	if fullpath[:5] != 'HKEY_':
		return Exception('Path must begin with with «HKEY_»')
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

def win_class_name(window=None)->str:
	''' Gets the name of the window class '''
	hwnd = win_get(window)
	if hwnd:
		return win32gui.GetClassName(hwnd)
	else:
		return None

def win_title_get(window=None)->str:
	''' Gets the title of the window.
	'''
	hwnd = win_get(window)
	if hwnd:
		return win32gui.GetWindowText(hwnd)
	else:
		return 'error: not found'

def win_title_set(window=None, new_title:str='')->int:
	''' Sets window title, returns hwnd.
	'''
	hwnd = win_get(window)
	if hwnd:
		win32gui.SetWindowText(hwnd, new_title)
		return hwnd

def win_list(title_filter:str=None
, class_filter:str=None
, case_sensitive:bool=False)->list:
	''' List titles of all the windows.
		title_filter and class_filter - optional filter
		class_filter - filter by window class name.
	'''
	
	def get_title(hwnd, _):
		title = win32gui.GetWindowText(hwnd)
		if not title: return
		titles.append(title)
	
	def get_class_name(hwnd, _):
		class_name = win32gui.GetClassName(hwnd)
		if class_name != class_filter: return
		titles.append(win32gui.GetWindowText(hwnd))
		
	titles = []
	func = get_class_name if class_filter else get_title
	win32gui.EnumWindows(
		func
		, None
	)
	if title_filter:
		if case_sensitive:
			title_filter = title_filter.lower()
			titles = [
				t for t in titles
					if title_filter in t.lower()
			]
		else:
			titles = [
				t for t in titles
					if title_filter in t
			]
	return titles

def win_find(title:str, exact:bool=True)->list:
	''' Find window handle by title.
		Returns list of found window handles.
	'''

	def check_title(hwnd, title:str):
		if exact:
			if win32gui.GetWindowText(hwnd) == title:
				result.append(hwnd)
		else:
			if title.lower() in win32gui.GetWindowText(hwnd).lower():
				result.append(hwnd)

	result = []
	win32gui.EnumWindows(check_title, title)
	return result

def win_activate(window=None)->int:
	''' Brings window to front, returns hwnd.'''
	hwnd = win_get(window)
	if not hwnd: return
	try:
		win32gui.SetForegroundWindow(hwnd)
	except pywintypes.error:
		cur_pos = mouse_pos_get()
		mouse_pos_set((-500, -500))
		try:
			win32gui.SetForegroundWindow(hwnd)
		except:
			pass
		mouse_pos_set(cur_pos)
	return hwnd

def win_act_rest(window=None)->int:
	'''
	Activates the window and restores it if it is minimized.
	'''
	if not (hwnd := win_get(window) ): return
	win_activate(hwnd)
	if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
	return hwnd

def win_minimize(window=None)->int:
	''' Minimize window. Returns hwnd.
	'''
	hwnd = win_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
		return hwnd
	
def win_maximize(window=None)->int:
	''' Maximize window. Returns hwnd.
	'''
	hwnd = win_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
		return hwnd

def win_restore(window=None)->int:
	''' Restore window. Returns hwnd.
	'''
	hwnd = win_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
		return hwnd

def win_show(window=None)->int:
	''' Show window. Returns hwnd.
	'''
	hwnd = win_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
		return hwnd

def win_hide(window=None)->int:
	''' Hide window. Returns hwnd.
	'''
	hwnd = win_get(window)
	if hwnd:
		win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
		return hwnd

def win_on_top(window=None, on_top:bool=True)->int:
	''' Sets the window to stay always on top.
	'''
	hwnd = win_get(window)
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
	millis = (int(uptime.uptime() * 1000) - win32api.GetLastInputInfo())
	return int( value_to_unit([millis, 'ms'], unit) )

def idle_wait(interval:int='1 sec')->int:
	' Suspends execution until user becomes active. '
	interval = value_to_unit(interval, 'ms')
	millis = interval
	prev_millis = millis
	while millis >= interval:
		time_sleep(interval / 1000)
		prev_millis = millis
		millis = (int(uptime.uptime() * 1000) - win32api.GetLastInputInfo())
		tdebug(interval, millis)
	return prev_millis


def _monitor(state:int=tcon.MONITOR_ON):
	_SendNotifyMessage(
		win32con.HWND_BROADCAST
		, win32con.WM_SYSCOMMAND
		, win32con.SC_MONITORPOWER
		, state
	)

def monitor_off():
	''' Turns off the monitor '''
	_monitor(state=tcon.MONITOR_OFF)

def monitor_on():
	''' Turns on the monitor '''
	_monitor(state=tcon.MONITOR_ON)
	


def win_is_visible(window=None)->bool:
	''' Is window visible?
	''' 
	hwnd = win_get(window)
	if hwnd:
		return win32gui.IsWindowVisible(hwnd) == 1
	else:
		return False

def win_close(window=None, wait:bool=True)->bool:
	'''
	Closes window and returns True on success.
	'''
	hwnd = win_get(window)
	if not hwnd: return False
	func = win32gui.SendMessage if wait else win32gui.PostMessage
	func(hwnd, win32con.WM_CLOSE, 0, 0)
	return True

def win_coor_get(window=None)->tuple:
	''' Returns coordinates of window:
		(top left x, y, bottom right x, y)
	'''
	hwnd = win_get(window)
	if hwnd: return win32gui.GetWindowRect(hwnd)



def win_list_top()->list:
	'''
	Gets a list of the top-level visible windows only.
	Returns list of tuples: (hwnd, 'title')
	'''
	def w_reaper(hwnd:int, lst:list):
		if not win32gui.IsWindowVisible(hwnd): return
		if any( c < -10 for c in win32gui.GetWindowRect(hwnd) ):
			return
		if ( title := win32gui.GetWindowText(hwnd) ):
			lst.append((hwnd, title))


	win_lst = []
	win32gui.EnumWindows(w_reaper, win_lst)
	return win_lst

def _test_reg_key():
	reg_key = 'HKEY_CURRENT_USER\\Software\\Microsoft\\Calc\\layout'
	input(
		reg_key + ' = ' + str(registry_get(reg_key))
		+ '\n\nPress enter to exit'
	)

_HWND = None

def _sound_cmd(cmd:int):
	global _HWND
	if not _HWND: _HWND = __builtins__['app'].app_hwnd
	win32gui.SendMessage(_HWND, _WM_APPCOMMAND, None, cmd)

def sound_vol_set(volume:int):
	'''
	It needs to be redone someday. Probably.
	'''
	for _ in range(50): _sound_cmd(_APPCOMMAND_VOLUME_DOWN)
	for _ in range(volume // 2): _sound_cmd(_APPCOMMAND_VOLUME_UP)

def sound_vol_up():
	_sound_cmd(_APPCOMMAND_VOLUME_UP)

def sound_vol_down():
	_sound_cmd(_APPCOMMAND_VOLUME_DOWN)

def sound_vol_mute():
	_sound_cmd(_APPCOMMAND_VOLUME_MUTE)

def mouse_pos_get()->tuple:
	' Returns mouse cursor position: (x, y) '
	try:
		return win32api.GetCursorPos()
	except pywintypes.error:
		return (0, 0)

def mouse_pos_set(pos:tuple):
	' Sets mouse cursor position '
	try:
		win32api.SetCursorPos(pos)
	except pywintypes.error:
		pass
def screen_size()->tuple:
	' Returns screen size: (width, height)'
	return (
		win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
		, win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
	)

def screen_width()->int:
	' Returns screen widht in pixels '
	return win32api.GetSystemMetrics(win32con.SM_CXSCREEN)

def screen_height()->int:
	' Returns screen height in pixels '
	return win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
if __name__ == '__main__':
	_test_reg_key()
else:
	patch_import()
