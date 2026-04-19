r'''
A *window* argument in function can be a
- *int* - it's the hwnd;
- *str* - it will find hwnd of window with that title;
- *None* - it will find hwnd of a foreground window.
'''
import os
import ctypes
import win32api
import win32gui
import win32con
import win32com
import winreg
import pywintypes
from datetime import datetime as dtime
import ctypes
import time
import psutil
from .tools import tprint, winapi, tcon, value_to_unit, dev_print \
, exc_text, app_pid
LockWorkStation = winapi.user32.LockWorkStation
_GetAncestor = winapi.user32.GetAncestor
_SendNotifyMessage = winapi.user32.SendNotifyMessageA
_GetACP = winapi.kernel32.GetACP
_WM_APPCOMMAND = 0x319
_APPCOMMAND_VOLUME_MUTE = 0x80000
_APPCOMMAND_VOLUME_DOWN = 0x90000
_APPCOMMAND_VOLUME_UP = 0xA0000
WIN_TASKBAR_CLS = 'Shell_TrayWnd'

def win_get(window=None, class_name:str|None=None)->int:
	r'''
	Returns window handle. If window is not specified then
	finds foreground window.
	You can use asterisk for imprecise search:

		asrt( win_get('Total Commander*'), 0, '>' )
		asrt( win_get('Non-existent window'), 0 )

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

def registry_path_add(fullpath:str)->bool|str:
	r'''
	Creates a new path in the registry.  
	Returns *True* on success or 'error text' on fail.  
	'''
	hive = fullpath.split('\\')[0]
	new_path = '\\'.join(fullpath.split('\\')[1:])
	if hive in [w for w in winreg.__dict__ if w[:5] == 'HKEY_']:
		hive = getattr(winreg, hive)
	else:
		return 'unknown hive'
	try:
		winreg.CreateKeyEx(hive, new_path)
		return True
	except:
		return exc_text()

def registry_get(fullpath:str):
	r'''
	Get value by fullpath to registry key.  
	*fullpath* - full path to the key.  
	Example:
		
		asrt(
			registry_get('HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Internet Explorer\\Build')
			, '922621'
		)

	'''
	if fullpath[:5] != 'HKEY_':
		return 'the fullpath must start with «HKEY_»'
	hive = fullpath.split('\\')[0]
	key_path = '\\'.join(fullpath.split('\\')[1:-1])
	key_name = fullpath.split('\\')[-1]
	if hive in [w for w in winreg.__dict__ if w[:5] == 'HKEY_']:
		hive = getattr(winreg, hive)
	else:
		return 'unknown hive'
	with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ) as reg_key:
		value, value_type = winreg.QueryValueEx(reg_key, key_name)
	return value

def registry_set(fullpath:str, value, value_type=None)->bool|str:
	r'''
	Set the value to the full path of the registry key.  
	*value_type* - type like `winreg.REG_SZ` or `winreg.REG_DWORD`.  
	If *value_type* is not specified: if type of value is *int*
	then store as *REG_DWORD*, otherwise store as *REG_SZ*.  
	If the key does not exist, it will be created.  
	*fullpath*  - full path to the key like this:  
	r'HKEY_CURRENT_USER\Software\Microsoft\Calc\layout'  
	Returns `True` on success or 'error text' on fail.  
	'''
	if fullpath[:5] != 'HKEY_':
		return 'the fullpath must start with «HKEY_»'
	hive = fullpath.split('\\')[0]
	key_path = '\\'.join(fullpath.split('\\')[1:-1])
	key_name = fullpath.split('\\')[-1]
	if value_type == None:
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
	except:
		return exc_text()

def win_class_name(window=None)->str|None:
	''' Gets the name of the window class '''
	hwnd = win_get(window)
	if hwnd:
		return win32gui.GetClassName(hwnd)
	else:
		return None

def win_title_get(window=None)->str:
	r'''
	Gets the title of the window.
	'''
	hwnd = win_get(window)
	if hwnd:
		return win32gui.GetWindowText(hwnd)
	else:
		return '<error: not found>'

def win_title_set(window=None, new_title:str='')->int:
	r'''
	Sets window title, returns hwnd.
	'''
	if not (hwnd := win_get(window)): return 0
	win32gui.SetWindowText(hwnd, new_title)
	return hwnd

def win_list(title_filter:str='', class_filter:str=''
, case_sensitive:bool=False)->list:
	r'''
	List titles of all the windows that have non-empty titles.  
	*title_filter* and *class_filter* - optional filters  
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
	win32gui.EnumWindows(func, None)
	if title_filter:
		if case_sensitive:
			title_filter = title_filter.lower()
			titles = [ t for t in titles if title_filter in t.lower() ]
		else:
			titles = [ t for t in titles if title_filter in t ]
	return titles

def win_find(title:str, exact:bool=True)->list:
	r'''
	Finds window handle by title.  
	Returns list of found window handles.  
	'''

	def check_title(hwnd, title:str):
		nonlocal result
		wtitle = win32gui.GetWindowText(hwnd)
		if title == '':
			pass
		if exact:
			if wtitle == title: result.append(hwnd)
		else:
			if title.lower() in wtitle.lower(): result.append(hwnd)

	result = []
	win32gui.EnumWindows(check_title, title)
	return result

def win_activate(window=None)->int:
	''' Brings window to front, returns hwnd.'''
	if not (hwnd := win_get(window)): return 0
	try:
		win32gui.SetForegroundWindow(hwnd)
	except pywintypes.error:
		cur_pos = mouse_pos_get()
		mouse_pos_set((-500, -500))
		try:
			win32gui.SetForegroundWindow(hwnd)
		except:
			mouse_pos_set(cur_pos)
			return 0
		mouse_pos_set(cur_pos)
	return hwnd

def win_act_rest(window=None)->int:
	r'''
	Activates the window and restores it if it is minimized.
	'''
	if not (hwnd := win_get(window) ): return -1
	win_activate(hwnd)
	if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
	return hwnd

def win_is_min(window)->bool|None:
	r'''
	Returns `True` if the window is minimized.

		asrt( win_is_min(win_get(class_name=WIN_TASKBAR_CLS)), False )

	'''
	if not (hwnd := win_get(window) ): return
	return win32gui.IsIconic(hwnd) != 0

def win_minimize(window=None)->int:
	r'''
	Minimizes window. Returns *hwnd*.
	'''
	hwnd = win_get(window)
	if hwnd: win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
	return hwnd
	
def win_maximize(window=None)->int:
	r'''
	Maximize window. Returns hwnd.
	'''
	if not (hwnd := win_get(window)): return 0
	win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
	return hwnd

def win_restore(window=None)->int:
	''' Restore window. Returns hwnd.
	'''
	if not (hwnd := win_get(window)): return 0
	win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
	return hwnd

def win_show(window=None)->int:
	r'''
	Shows window. Returns hwnd.  
	'''
	if not (hwnd := win_get(window)): return 0
	win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
	return hwnd

def win_hide(window=None)->int:
	r'''
	Hide window. Returns hwnd.
	'''
	if not (hwnd := win_get(window)): return 0
	win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
	return hwnd

def win_on_top(window=None, on_top:bool=True)->int:
	r'''
	Sets the window to stay always on top.
	'''
	if not (hwnd := win_get(window)): return 0
	try:
		win32gui.SetWindowPos(
			hwnd
			, win32con.HWND_TOPMOST if on_top else win32con.HWND_NOTOPMOST
			, 0, 0, 0, 0
			, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE
		)
	except: pass
	return hwnd



def _idle_millis()->int:
	'''
	Returns idle time in milliseconds.
	'''
	C_ULONG_MAX = 4294967295
	cur_time = win32api.GetTickCount()
	last_input = win32api.GetLastInputInfo()
	while cur_time > C_ULONG_MAX: cur_time -= C_ULONG_MAX
	return cur_time - last_input

def idle_duration(unit:str='sec')->int:
	r'''
	Returns idle time in specified units ('msec', 'sec', 'min', 'hour').  

		asrt( bmark(idle_duration), 2_500 )

	'''
	return int( value_to_unit((_idle_millis(), 'ms'), unit=unit) )

def idle_wait(interval:int|str='1 sec')->int:
	r'''
	Suspends execution until user becomes active.  
	Returns the number of milliseconds the user has been inactive.  
	*interval* - inactivity check interval.  
	'''
	interval = int(value_to_unit(interval, 'ms'))
	wait_sec:float = interval / 1000
	millis = interval
	prev_millis:int = millis
	while millis >= interval:
		time.sleep(wait_sec)
		prev_millis = millis
		millis = _idle_millis()
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
	if not (hwnd := win_get(window)): return False
	func = win32gui.SendMessage if wait else win32gui.PostMessage
	func(hwnd, win32con.WM_CLOSE, 0, 0)
	return True

def win_coor_get(window=None)->tuple:
	r'''
	Returns coordinates of window: (top left x, y, bottom right x, y)
	'''
	if not (hwnd := win_get(window)): return ()
	return win32gui.GetWindowRect(hwnd)

def win_exists(window=None)->bool:
	r'''
	Does the window still exist?  

		asrt( win_exists(win_get('Taskop*')), True )
		asrt( win_exists(win_get('Taskopyy')), False )
		asrt( bmark(win_exists, (0,)), 1500 )
		asrt( bmark(win_exists, ('Taskopy',)), 7_000 )

	'''
	return win32gui.IsWindow(win_get(window)) == 1

def win_texts(window, child_class_name:str='')->set[str]:
	r'''
	Retrieves text of child controls.  
	'''

	def _enum_all(hwnd, callback):
		callback(hwnd)
		def _inner(child, _):
			_enum_all(child, callback)
		win32gui.EnumChildWindows(hwnd, _inner, None)	

	def _get_texts(ch_hwnd):
		txt = ''
		if not child_class_name:
			txt = win32gui.GetWindowText(ch_hwnd)
		elif win32gui.GetClassName(ch_hwnd) == child_class_name:
			txt = win32gui.GetWindowText(ch_hwnd)
		if txt and not txt.isspace(): texts.add(txt)
	texts:set[str] = set()
	if not (hwnd := win_get(window) ): return texts
	_enum_all(hwnd, _get_texts)
	return texts



def win_list_top()->list:
	r'''
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
	r'''
	Returns mouse cursor position: (x, y).

		asrt( bmark(mouse_pos_get), 2_300 )

	'''
	try:
		return win32api.GetCursorPos()
	except pywintypes.error:
		return (0, 0)

def mouse_pos_set(pos:tuple):
	r'''
	Sets mouse cursor position.

		asrt( bmark(mouse_pos_set, ((500, 500) ,)), 5_000 )

	'''
	try:
		win32api.SetCursorPos(pos)
	except pywintypes.error:
		pass

def mouse_lclick():
	' Left click '
	win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0,0,0)
	win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0,0,0)

def mouse_rclick():
	' Right click'
	win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN,0,0,0,0)
	win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP,0,0,0,0)

def mouse_move(dx:int, dy:int):
	' Move the mouse by relative coordinates '
	win32api.mouse_event(win32con.MOUSEEVENTF_MOVE,dx,dy,0,0)

def mouse_scroll(delta:int):
	' Vertical mouse scrolling '
	win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL,0,0,delta,0)

def mouse_hscroll(delta:int):
	' Horizontal mouse scrolling '
	win32api.mouse_event(win32con.MOUSEEVENTF_HWHEEL,0,0,delta,0)
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

def sys_codepage():
	r'''
	Returns current Windows code page for non-unicode programs.

		asrt( sys_codepage(), 'cp1251' )
		asrt( bmark(sys_codepage), 2100 )

	'''
	return 'cp' + str(_GetACP())

def sys_shutdown(timeout:int=0):
	r'''
	Shutting down this computer.  
	*timeout* - set the time-out period before shutdown in seconds.
	'''
	os.system(f'shutdown -s -t {timeout}')

def is_sys_locked()->bool:
	r'''
	Is Windows locked?  
	Note: seems not to be very reliable.  
	'''
	return win32gui.GetForegroundWindow() == 0

def sys_is_server()->bool:
	r'''
	Is this computer a Windows Server?

		asrt( bmark(sys_is_server), 3_700 )
	
	'''
	return win32api.GetVersionEx(1)[8] != 1

def sys_start_time()->dtime:
	r'''
	Returns system startup time (local time).

		asrt( bmark(sys_start_time), 1_800 )

	'''
	return dtime.fromtimestamp(psutil.boot_time())

def sys_is_defender_on()->bool:
	r'''
	Is real-time protection is on?  
	Not cheap:

		asrt( bmark(sys_is_defender_on, b_iter=3), 79_000_000 )
		
	'''
	defender = win32com.client.GetObject('winmgmts:\\\\.\\root\\Microsoft\\Windows\\Defender')
	status = defender.ExecQuery('SELECT * FROM MSFT_MpComputerStatus')[0]
	enabled = bool(status.RealTimeProtectionEnabled)
	defender = None
	return enabled

def sys_layout_to_lang(hkl:int)->str:
	r'''
	Converts the HKL (value from GetKeyboardLayout) to a two-part language code.  
	Example:

		hkl = win32api.GetKeyboardLayout()
		qprint( sys_layout_to_lang(hkl) )

	'''
	LOCALE_SNAME = 0x0000005c
	FALLBACK = '<fail>'
	try:
		lang_id = hkl & 0xFFFF
		buffer = ctypes.create_unicode_buffer(8)
		result = winapi.kernel32.GetLocaleInfoW(
			lang_id
			, LOCALE_SNAME
			, buffer
			, len(buffer)
		)
		if result > 0:
			return buffer.value.lower()
		else:
			dev_print(f'bad result = {result}')
			return FALLBACK
	except Exception as err:
		dev_print(err)
		return FALLBACK

def sys_kboard_lang_get()->str:
	r'''
	Gets current keyboard layout.  

		asrt( bmark(sys_kboard_lang_get), 7_000 )

	'''
	hkl = win32api.GetKeyboardLayout()
	return sys_layout_to_lang(hkl)

def sys_lang_to_layout(lang:str)->int:
	r'''
	Convert a language code (e.g. "en", "ru", "en-US", "de-DE") 
	to Windows keyboard layout ID (HKL) without any hardcoded dictionary.
	
	Returns the integer layout_id ready for WM_INPUTLANGCHANGEREQUEST.

		asrt( bmark(sys_lang_to_layout, ('en-us',)), 5_300 )

	'''
	lang = lang.strip().lower().replace('_', '-')
	if len(lang) == 2: lang += '-' + lang
	lcid = winapi.kernel32.LocaleNameToLCID(ctypes.create_unicode_buffer(lang), 0)
	if lcid == 0:
		dev_print('fallback without country')
		base_lang = lang.split("-")[0]
		lcid = winapi.kernel32.LocaleNameToLCID(ctypes.create_unicode_buffer(base_lang), 0)
	if lcid == 0:
		raise ValueError(
			f'Could not resolve language code "{lang}" to a valid Windows locale. '
			'Make sure the language is installed in Windows Settings.'
		)
	layout_id = (lcid << 16) | lcid
	return layout_id

def sys_kboard_lang_set(layout_id_or_lang:int|str)->bool:
	r'''
	Change keyboard layout for the foreground window.  
	Accepts either raw int layout_id OR language string
	like 'en-us', 'ru-ru'.  
	Returns `True` on success.  

		asrt( bmark(sys_kboard_lang_set, ('en-us',)), 150_000 )

	'''
	if isinstance(layout_id_or_lang, str):
		try:
			layout_id = sys_lang_to_layout(layout_id_or_lang)
		except ValueError as err:
			dev_print(err)
			return False
	else:
		layout_id = layout_id_or_lang
	hwnd = win32gui.GetForegroundWindow()
	if not hwnd:
		dev_print('No foreground window found')
		return False
	result = win32api.SendMessage(hwnd, win32con.WM_INPUTLANGCHANGEREQUEST
	, 0, layout_id)
	return result == 0
