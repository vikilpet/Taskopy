r'''
A *window* argument in function can be a
- *int* - it's the hwnd;
- *str* - it will find hwnd of window with that title;
- *None* - it will find hwnd of a foreground window.
'''
import os
import functools
import win32api
import win32gui
import win32con
import win32com
import win32process
import win32pdh
import winreg
import pywintypes
from datetime import datetime as dtime
import ctypes
from ctypes import c_float, c_void_p, POINTER
from ctypes.wintypes import DWORD, BOOL
from ctypes import wintypes
import time
import psutil
from enum import IntEnum, IntFlag
from .tools import tprint, tcon, value_to_unit, dev_print \
, exc_text, app_pid
import plugins.winapi as winapi
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

def win_find(title:str='', exact:bool=True, class_name:str|None=None)->list:
	r'''
	Finds window handle by title and/or class_name.
	Returns list of found window handles.
	'''

	def check_window(hwnd, _):
		nonlocal result
		wtitle = win32gui.GetWindowText(hwnd)
		if title:
			if exact:
				if wtitle != title:
					return
			else:
				if title not in wtitle.lower():
					return
		if class_name is not None:
			wclass = win32gui.GetClassName(hwnd)
			if exact:
				if wclass != class_name:
					return
			else:
				if class_name not in wclass.lower():
					return
		result.append(hwnd)

	if title and not exact: title = title.lower()
	if class_name and not exact: class_name = class_name.lower()
	result = []
	win32gui.EnumWindows(check_window, None)
	return result

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

def win_is_fullscreen(window=None):
	r'''
	Check if a window is in full-screen mode by comparing its
	rect to the monitor rect.
	'''
	if not (hwnd := win_get(window) ): return False
	if not win32gui.IsWindowVisible(hwnd): return False
	if win32gui.IsIconic(hwnd): return False
	left, top, right, bottom = win32gui.GetWindowRect(hwnd)
	window_width = right - left
	window_height = bottom - top
	monitor_info = win32api.GetMonitorInfo(
		win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
	)
	monitor_rect = monitor_info["Monitor"]  # (left, top, right, bottom)
	monitor_width = monitor_rect[2] - monitor_rect[0]
	monitor_height = monitor_rect[3] - monitor_rect[1]
	return (
		window_width >= monitor_width
		and window_height >= monitor_height
		and left <= monitor_rect[0]
		and top <= monitor_rect[1]
	)
	
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
	r'''
	Returns idle time in milliseconds.
	'''
	C_ULONG_MAX = 4294967295
	cur_time = win32api.GetTickCount()
	last_input = win32api.GetLastInputInfo()
	while cur_time > C_ULONG_MAX: cur_time -= C_ULONG_MAX
	return cur_time - last_input

def _idle_millis_kb()->int:
	r'''
	Returns idle time in milliseconds from built-in hook.
	'''
	delta = dtime.now() - app.tasks.hook_kb.last_input_time
	return int(delta.total_seconds() * 1000)

def idle_duration(unit:str='sec', by_keyboard:bool=False)->int:
	r'''
	Returns idle time in specified units ('msec', 'sec', 'min', 'hour').  
	*by_keyboard* - use last input time from the internal keyboard hook.  
	Rationale: A system-level inactivity timer may be triggered by
	various events, such as signals from a wireless mouse.  

		asrt( bmark(idle_duration), 4_000 )

	'''
	millis = _idle_millis_kb() if by_keyboard else _idle_millis()
	return int( value_to_unit((millis, 'ms'), unit=unit) )

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
	win32gui.SendMessage(
		win32con.HWND_BROADCAST,
		win32con.WM_SYSCOMMAND,
		win32con.SC_MONITORPOWER,
		2
	)

def monitor_off():
	''' Turns off the monitor(s) '''
	_monitor(state=tcon.MONITOR_OFF)

def monitor_on():
	''' Turns on the monitor(s) '''
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
	r'''
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
		asrt( bmark(win_exists, ('Taskopy',)), 25_000 )

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

def proc_by_win(window) -> int:
	r'''
	Returns the Process ID (PID) for a given window handle (HWND).  
	*hwnd*: The window handle (HWND). Can be 0 or None for invalid windows.  
	'''
	if not (hwnd := win_get(window)): return 0
	try:
		return win32process.GetWindowThreadProcessId(hwnd)[1]
	except Exception:
		dev_print(exc_text())
		return 0

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

def icon_file_load(ico_path:str
, icon_index:int=0)->tuple[winapi.HICON, winapi.HICON]:
	r'''
	Load small and large icons from a .ico file.
	Returns (hicon_small, hicon_large) or (None, None) on failure.
	'''
	phicon_large = (winapi.HICON * 1)()
	phicon_small = (winapi.HICON * 1)()
	n = winapi.shell32.ExtractIconExW(ico_path, icon_index, phicon_large, phicon_small, 1)
	if n > 0: return phicon_small[0], phicon_large[0]
	return None, None

def win_icon_set(window, hicon:int)->bool:
	r'''
	Set both small and large icon using your HICON handle.
	'''
	if not (hwnd := win_get(window)): return False
	winapi.user32.SendMessageW(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, hicon)
	winapi.user32.SendMessageW(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, hicon)
	return True
_CLSID_MMDeviceEnumerator = winapi.GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
_IID_IMMDeviceEnumerator  = winapi.GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
_IID_IAudioEndpointVolume = winapi.GUID('{5CDF2C82-841E-4546-9722-0CF74078229A}')
_eRender     = 0
_eMultimedia = 1
_IMMDeviceEnumerator_GetDefaultAudioEndpoint     = 4
_IMMDevice_Activate                              = 3
_IAudioEndpointVolume_SetMasterVolumeLevelScalar = 7
_IAudioEndpointVolume_GetMasterVolumeLevelScalar = 9
_IAudioEndpointVolume_SetMute                    = 14
_IAudioEndpointVolume_GetMute                    = 15
_IMMDevice_OpenPropertyStore  = 4
_IPropertyStore_GetValue       = 5
_IMMDeviceEnumerator_EnumAudioEndpoints = 3
_IMMDeviceCollection_GetCount             = 3
_IMMDeviceCollection_Item                  = 4
_IMMDevice_GetId    = 5
_IMMDevice_GetState = 6
_CLSID_CPolicyConfigClient = winapi.GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")
_IID_IPolicyConfig = winapi.GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
_IPolicyConfig_SetDefaultEndpoint = 13
_eConsole         = 0
_eMultimedia      = 1
_eCommunications  = 2


class SoundDevType(IntEnum):
	'''EDataFlow — direction of audio data flow.'''
	RENDER  = 0   # output / playback / speakers
	CAPTURE = 1   # input  / recording / microphone


class SoundDevState(IntFlag):
	'''DEVICE_STATE_* flags describing endpoint availability.'''
	ACTIVE     = 0x00000001
	DISABLED   = 0x00000002
	NOTPRESENT = 0x00000004
	UNPLUGGED  = 0x00000008
	ALL        = 0x0000000F
_STGM_READ = 0x00000000
_VT_LPWSTR = 31
class _PROPERTYKEY(ctypes.Structure):
	_fields_ = [("fmtid", winapi.GUID), ("pid", DWORD)]

_PKEY_Device_FriendlyName = _PROPERTYKEY(
	winapi.GUID("{a45c254e-df1c-4efd-8020-67d146a850e0}"), 14
)
class _PROPVARIANT(ctypes.Structure):
	_fields_ = [
		("vt",        ctypes.c_ushort),
		("wReserved1", ctypes.c_ushort),
		("wReserved2", ctypes.c_ushort),
		("wReserved3", ctypes.c_ushort),
		("ptr",       ctypes.c_void_p),   # union — for VT_LPWSTR this is a PWSTR
		("_pad",      ctypes.c_void_p),   # extra space (DECIMAL / array members)
	]

def _sound_endpoint() -> c_void_p:
	"""Return an activated IAudioEndpointVolume pointer.
	Caller must winapi.com_release() it when done."""
	winapi.ole32.CoInitializeEx(None, winapi.COINIT_APARTMENTTHREADED)
	enum_ptr = c_void_p()
	winapi.ole32.CoCreateInstance(
		ctypes.byref(_CLSID_MMDeviceEnumerator),
		None, winapi.CLSCTX_ALL,
		ctypes.byref(_IID_IMMDeviceEnumerator),
		ctypes.byref(enum_ptr),
	)
	device_ptr = c_void_p()
	try:
		winapi.com_vcall(
			enum_ptr, _IMMDeviceEnumerator_GetDefaultAudioEndpoint,
			ctypes.HRESULT, [DWORD, DWORD, POINTER(c_void_p)],
			_eRender, _eMultimedia, ctypes.byref(device_ptr),
		)
	finally:
		winapi.com_release(enum_ptr)
	vol_ptr = c_void_p()
	try:
		winapi.com_vcall(
			device_ptr, _IMMDevice_Activate,
			ctypes.HRESULT,
			[POINTER(winapi.GUID), DWORD, c_void_p, POINTER(c_void_p)],
			ctypes.byref(_IID_IAudioEndpointVolume),
			winapi.CLSCTX_ALL, None, ctypes.byref(vol_ptr),
		)
	finally:
		winapi.com_release(device_ptr)
	return vol_ptr

def sound_vol_get() -> float:
	'Return current master output volume in [0.0, 1.0].'
	p = _sound_endpoint()
	try:
		out = c_float()
		winapi.com_vcall(
			p, _IAudioEndpointVolume_GetMasterVolumeLevelScalar,
			ctypes.HRESULT, [POINTER(c_float)], ctypes.byref(out),
		)
		return out.value
	finally:
		winapi.com_release(p)

def sound_vol_set(level: float) -> None:
	'Set master output volume. `level` is in [0.0, 1.0].'
	if not 0.0 <= level <= 1.0:
		raise ValueError('level must be between 0.0 and 1.0')
	p = _sound_endpoint()
	try:
		winapi.com_vcall(
			p, _IAudioEndpointVolume_SetMasterVolumeLevelScalar,
			ctypes.HRESULT, [c_float, POINTER(winapi.GUID)],
			c_float(level), None,
		)
	finally:
		winapi.com_release(p)

def sound_vol_add(delta: float) -> float:
	r'''
	Change master volume by `delta` (e.g. +0.05 or -0.10).
	Clamps to [0.0, 1.0] and returns the new volume.
	'''
	p = _sound_endpoint()
	try:
		cur = c_float()
		winapi.com_vcall(
			p, _IAudioEndpointVolume_GetMasterVolumeLevelScalar,
			ctypes.HRESULT, [POINTER(c_float)], ctypes.byref(cur),
		)
		new = cur.value + delta
		if   new < 0.0: new = 0.0
		elif new > 1.0: new = 1.0
		winapi.com_vcall(
			p, _IAudioEndpointVolume_SetMasterVolumeLevelScalar,
			ctypes.HRESULT, [c_float, POINTER(winapi.GUID)],
			c_float(new), None,
		)
		return new
	finally:
		winapi.com_release(p)

def sound_mute_get() -> bool:
	'Return current master mute state.'
	p = _sound_endpoint()
	try:
		out = BOOL()
		winapi.com_vcall(
			p, _IAudioEndpointVolume_GetMute,
			ctypes.HRESULT, [POINTER(BOOL)], ctypes.byref(out),
		)
		return bool(out.value)
	finally:
		winapi.com_release(p)

def sound_mute_set(mute: bool) -> None:
	'Set master mute state.'
	p = _sound_endpoint()
	try:
		winapi.com_vcall(
			p, _IAudioEndpointVolume_SetMute,
			ctypes.HRESULT, [BOOL, POINTER(winapi.GUID)],
			BOOL(bool(mute)), None,
		)
	finally:
		winapi.com_release(p)

def sound_device_name() -> str|None:
	r'''
	Return the friendly name of the default render device.  

		asrt( bmark(sound_device_name), 8_800_000 )
	
	'''
	winapi.ole32.CoInitializeEx(None, winapi.COINIT_APARTMENTTHREADED)
	enum_ptr = ctypes.c_void_p()
	winapi.ole32.CoCreateInstance(
		ctypes.byref(_CLSID_MMDeviceEnumerator),
		None, winapi.CLSCTX_ALL,
		ctypes.byref(_IID_IMMDeviceEnumerator),
		ctypes.byref(enum_ptr),
	)
	device_ptr = ctypes.c_void_p()
	try:
		winapi.com_vcall(
			enum_ptr, _IMMDeviceEnumerator_GetDefaultAudioEndpoint,
			ctypes.HRESULT, [DWORD, DWORD, POINTER(ctypes.c_void_p)],
			_eRender, _eMultimedia, ctypes.byref(device_ptr),
		)
	finally:
		winapi.com_release(enum_ptr)
	try:
		props_ptr = ctypes.c_void_p()
		winapi.com_vcall(
			device_ptr, _IMMDevice_OpenPropertyStore,
			ctypes.HRESULT, [DWORD, POINTER(ctypes.c_void_p)],
			_STGM_READ, ctypes.byref(props_ptr),
		)
	finally:
		winapi.com_release(device_ptr)
	try:
		pv = _PROPVARIANT()
		winapi.com_vcall(
			props_ptr, _IPropertyStore_GetValue,
			ctypes.HRESULT,
			[POINTER(_PROPERTYKEY), POINTER(_PROPVARIANT)],
			ctypes.byref(_PKEY_Device_FriendlyName),
			ctypes.byref(pv),
		)
		if pv.vt == _VT_LPWSTR and pv.ptr:
			return ctypes.wstring_at(pv.ptr)
		return None
	finally:
		winapi.com_release(props_ptr)

def sound_device_list(
	data_flow:SoundDevType = SoundDevType.RENDER,
	state_mask:SoundDevState = SoundDevState.ACTIVE,
) -> list[tuple[str, str]]:
	'''
	Return `(friendly_name, device_id)` tuples for each matching endpoint.

	*data_flow* - `RENDER` for playback devices
	, `CAPTURE` for recording devices.  
	*state_mask* - bitwise-OR of device states to
	include (default: ACTIVE only).  

		asrt( bmark(sound_device_list), 9_800_000 )
	
	'''
	winapi.ole32.CoInitializeEx(None, winapi.COINIT_APARTMENTTHREADED)
	enum_ptr = ctypes.c_void_p()
	winapi.ole32.CoCreateInstance(
		ctypes.byref(_CLSID_MMDeviceEnumerator),
		None, winapi.CLSCTX_ALL,
		ctypes.byref(_IID_IMMDeviceEnumerator),
		ctypes.byref(enum_ptr),
	)
	coll_ptr = ctypes.c_void_p()
	try:
		winapi.com_vcall(
			enum_ptr, _IMMDeviceEnumerator_EnumAudioEndpoints,
			ctypes.HRESULT,
			[DWORD, DWORD, POINTER(ctypes.c_void_p)],
			int(data_flow), int(state_mask), ctypes.byref(coll_ptr),
		)
	finally:
		winapi.com_release(enum_ptr)
	try:
		count = DWORD(0)
		winapi.com_vcall(
			coll_ptr, _IMMDeviceCollection_GetCount,
			ctypes.HRESULT, [POINTER(DWORD)],
			ctypes.byref(count),
		)
		results: list[tuple[str, str]] = []
		for i in range(count.value):
			device_ptr = ctypes.c_void_p()
			winapi.com_vcall(
				coll_ptr, _IMMDeviceCollection_Item,
				ctypes.HRESULT,
				[DWORD, POINTER(ctypes.c_void_p)],
				i, ctypes.byref(device_ptr),
			)
			try:
				id_ptr = ctypes.c_wchar_p()
				winapi.com_vcall(
					device_ptr, _IMMDevice_GetId,
					ctypes.HRESULT, [POINTER(ctypes.c_wchar_p)],
					ctypes.byref(id_ptr),
				)
				device_id = id_ptr.value or ""
				props_ptr = ctypes.c_void_p()
				winapi.com_vcall(
					device_ptr, _IMMDevice_OpenPropertyStore,
					ctypes.HRESULT, [DWORD, POINTER(ctypes.c_void_p)],
					_STGM_READ, ctypes.byref(props_ptr),
				)
				try:
					pv = _PROPVARIANT()
					winapi.com_vcall(
						props_ptr, _IPropertyStore_GetValue,
						ctypes.HRESULT,
						[POINTER(_PROPERTYKEY), POINTER(_PROPVARIANT)],
						ctypes.byref(_PKEY_Device_FriendlyName),
						ctypes.byref(pv),
					)
					if pv.vt == _VT_LPWSTR and pv.ptr:
						name = ctypes.wstring_at(pv.ptr)
					else:
						name = ""
				finally:
					winapi.com_release(props_ptr)
			finally:
				winapi.com_release(device_ptr)
			results.append((name, device_id))
		return results
	finally:
		winapi.com_release(coll_ptr)

def sound_device_set(device_id:str)->bool:
	r'''
	Set the default audio device for all roles.

	Parameters
	----------
	device_id : str
		Opaque device ID string as returned by :func:`sound_device_list`
		(the second element of each tuple).

	Returns `True` if the call succeeded.  
	'''
	winapi.ole32.CoInitializeEx(None, winapi.COINIT_APARTMENTTHREADED)
	policy_ptr = ctypes.c_void_p()
	winapi.ole32.CoCreateInstance(
		ctypes.byref(_CLSID_CPolicyConfigClient),
		None, winapi.CLSCTX_ALL,
		ctypes.byref(_IID_IPolicyConfig),
		ctypes.byref(policy_ptr),
	)
	try:
		for role in (_eConsole, _eMultimedia, _eCommunications):
			winapi.com_vcall(
				policy_ptr, _IPolicyConfig_SetDefaultEndpoint,
				ctypes.HRESULT,
				[ctypes.c_wchar_p, DWORD],
				device_id, role,
			)
		return True
	finally:
		winapi.com_release(policy_ptr)

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

@functools.cache
def sys_codepage():
	r'''
	Returns current Windows code page for non-unicode programs.

		asrt( sys_codepage(), 'cp1251' )
		asrt( bmark(sys_codepage), 1500 )

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

@functools.cache
def sys_is_server()->bool:
	r'''
	Is this computer a Windows Server?

		asrt( bmark(sys_is_server), 3_000 )
	
	'''
	return win32api.GetVersionEx(1)[8] != 1

@functools.cache
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


class CpuUsageMonitor:
	r'''
	Monitor total CPU usage matching Task Manager (Windows 8+).  
	Should match *Task Manager*  
	Usage example:

		with CpuUsageMonitor() as monitor:
			for _ in range(5):
				print(f"CPU: {monitor.read():.1f}%")

	'''

	def __init__(self, sleep_interval:float=1.0):
		self.sleep_interval = sleep_interval
		self._hq = win32pdh.OpenQuery()
		self._hc_busy = win32pdh.AddCounter(
			self._hq,
			r"\Processor Information(_Total)\% Processor Time",
		)
		self._hc_queue = win32pdh.AddCounter(
			self._hq,
			r"\System\Processor Queue Length",
		)
		win32pdh.CollectQueryData(self._hq)

	def read(self):
		"""Return current CPU busy percentage (0.0 - 100.0)."""
		time.sleep(self.sleep_interval)
		win32pdh.CollectQueryData(self._hq)
		_type, value = win32pdh.GetFormattedCounterValue(
			self._hc_busy, win32pdh.PDH_FMT_DOUBLE
		)
		return max(0.0, min(100.0, value))

	def is_saturated(
		self,
		busy_threshold=85.0,
		queue_per_core=2.0,
		logical_cores=None,
	):
		"""
		Return True if the CPU appears to be a bottleneck.

		Saturation is confirmed when BOTH:
		* % Processor Time >= busy_threshold, AND
		* Processor Queue Length >= queue_per_core * logical_cores

		Per Microsoft guidance:
		- busy_threshold85%: "system might work slowly"
		- queue_per_core 2:   warning level (>2 per processor with high CPU => investigate)
		- queue_per_core 10:  definite bottleneck (server workload)

		Args:
			busy_threshold:   Sustained % Processor Time that counts as
							"high" (0-100). Default 85.
			queue_per_core:    Queue-length-per-core threshold. Default 2
							(Microsoft warning). Use 10 for "definitely
							bottlenecked" on servers.
			logical_cores: Logical processor count. Auto-detected via
							os.cpu_count() if None.

		Returns:
			dict with:
				saturated (bool)   - True if CPU is a bottleneck
				busy_pct (float)  - % Processor Time
				queue_len   (float)  - Processor Queue Length
				queue_limit (float)  - queue threshold that was applied
		"""
		if logical_cores is None:
			logical_cores = os.cpu_count() or 1
		queue_limit = queue_per_core * logical_cores

		time.sleep(self.sleep_interval)
		win32pdh.CollectQueryData(self._hq)

		fmt = win32pdh.PDH_FMT_DOUBLE
		_, busy = win32pdh.GetFormattedCounterValue(self._hc_busy, fmt)
		_, queue = win32pdh.GetFormattedCounterValue(self._hc_queue, fmt)

		busy = max(0.0, min(100.0, busy))
		saturated = (busy >= busy_threshold) and (queue >= queue_limit)

		return {
			"saturated": saturated,
			"busy_pct": busy,
			"queue_len": queue,
			"queue_limit": queue_limit,
		}

	def close(self):
		for hc in (getattr(self, "_hc_busy", None),
				getattr(self, "_hc_queue", None)):
			if hc is not None:
				try:
					win32pdh.RemoveCounter(hc)
				except Exception:
					pass
		self._hc_busy = self._hc_queue = None
		if getattr(self, "_hq", None) is not None:
			try:
				win32pdh.CloseQuery(self._hq)
			except Exception:
				pass
		self._hq = None

	def __enter__(self):
		return self

	def __exit__(self, *exc_info):
		self.close()

	def __del__(self):
		self.close()


def sys_cpu_usage(sleep_interval=1.0)->float:
	r'''
	Return total CPU usage (%) matching Task Manager.  
	Suitable for occasional use (not tight loops).  
	*sleep_interval* - Seconds between the two samples needed
	to compute the rate. 1.0 matches Task
	Manager's update interval.  
	'''
	hq = win32pdh.OpenQuery()
	try:
		hc = win32pdh.AddCounter(
			hq, r"\Processor Information(_Total)\% Processor Utility"
		)
		try:
			win32pdh.CollectQueryData(hq)        # seed baseline
			time.sleep(sleep_interval)
			win32pdh.CollectQueryData(hq)        # take the sample
			_type, value = win32pdh.GetFormattedCounterValue(
				hc, win32pdh.PDH_FMT_DOUBLE
			)
			return round(value, 1)
		finally:
			win32pdh.RemoveCounter(hc)
	finally:
		win32pdh.CloseQuery(hq)

class RamUsageMonitor:
	r'''
	Monitor free RAM and detect memory saturation.  
	'''

	def __init__(self, sleep_interval=1.0):
		self.sleep_interval = sleep_interval
		self._hq = win32pdh.OpenQuery()
		self._hc_avail = win32pdh.AddCounter(
			self._hq, r"\Memory\Available MBytes"
		)
		self._hc_commit = win32pdh.AddCounter(
			self._hq, r"\Memory\% Committed Bytes In Use"
		)
		self._hc_pages = win32pdh.AddCounter(
			self._hq, r"\Memory\Pages/sec"
		)
		win32pdh.CollectQueryData(self._hq)
		self._total_mb = self._get_total_physical_mb()

	@staticmethod
	def _get_total_physical_mb():
		"""Get total physical RAM in MB via GlobalMemoryStatusEx."""
		class MEMORYSTATUSEX(ctypes.Structure):
			_fields_ = [
				("dwLength", ctypes.c_uint32),
				("dwMemoryLoad", ctypes.c_uint32),
				("ullTotalPhys", ctypes.c_uint64),
				("ullAvailPhys", ctypes.c_uint64),
				("ullTotalPageFile", ctypes.c_uint64),
				("ullAvailPageFile", ctypes.c_uint64),
				("ullTotalVirtual", ctypes.c_uint64),
				("ullAvailVirtual", ctypes.c_uint64),
				("ullAvailExtendedVirtual", ctypes.c_uint64),
			]

		stat = MEMORYSTATUSEX()
		stat.dwLength = ctypes.sizeof(stat)
		ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
		return stat.ullTotalPhys // (1024 * 1024)

	def read(self):
		"""
		Return current memory status.

		Returns:
			dict with:
				available_mb (float)  - free + standby, immediately usable
				total_mb     (int)    - total installed physical RAM
				used_mb      (float)  - total - available
				used_pct     (float)  - used as % of total
				commit_pct   (float)  - committed bytes / commit limit * 100
				pages_per_sec(float)  - page fault rate (hard paging)
		"""
		time.sleep(self.sleep_interval)
		win32pdh.CollectQueryData(self._hq)

		fmt = win32pdh.PDH_FMT_DOUBLE
		_, avail = win32pdh.GetFormattedCounterValue(self._hc_avail, fmt)
		_, pages = win32pdh.GetFormattedCounterValue(self._hc_pages, fmt)
		_, commit = win32pdh.GetFormattedCounterValue(self._hc_commit, fmt)

		avail = max(0.0, avail)
		used = max(0.0, self._total_mb - avail)
		used_pct = (used / self._total_mb * 100.0) if self._total_mb else 0.0

		return {
			"available_mb": avail,
			"total_mb": self._total_mb,
			"used_mb": used,
			"used_pct": used_pct,
			"commit_pct": commit,
			"pages_per_sec": pages,
		}

	def is_saturated(
		self,
		available_mb_threshold=256,
		pages_per_sec_threshold=50,
		commit_pct_threshold=90.0,
	):
		"""
		Return True if the system is experiencing memory pressure.

		Saturation is confirmed when BOTH:
		* Available MBytes <= available_mb_threshold (very low free RAM), AND
		* Pages/sec >= pages_per_sec_threshold (system is hard-paging)

		Additionally, if commit charge is near the limit
		(commit_pct >= commit_pct_threshold), the system is at risk of
		running out of virtual memory entirely.

		Args:
			available_mb_threshold: Available MB below which RAM is
									considered critically low. Default 256.
			pages_per_sec_threshold: Paging rate that indicates the
									system is thrashing. Default 50
									(Microsoft: sustained >5/sec warrants
									attention; >50 = serious).
			commit_pct_threshold:   % Committed Bytes In Use that signals
									virtual memory exhaustion risk.

		Returns:
			dict with:
				saturated   (bool)   - True if memory is a bottleneck
				available_mb(float)  - current available RAM
				pages_per_sec(float) - current paging rate
				commit_pct  (float)  - current commit charge %
				reason      (str)    - human-readable explanation
		"""
		time.sleep(self.sleep_interval)
		win32pdh.CollectQueryData(self._hq)

		fmt = win32pdh.PDH_FMT_DOUBLE
		_, avail = win32pdh.GetFormattedCounterValue(self._hc_avail, fmt)
		_, pages = win32pdh.GetFormattedCounterValue(self._hc_pages, fmt)
		_, commit = win32pdh.GetFormattedCounterValue(self._hc_commit, fmt)

		avail = max(0.0, avail)

		low_ram = avail <= available_mb_threshold
		thrashing = pages >= pages_per_sec_threshold
		commit_risk = commit >= commit_pct_threshold
		saturated = low_ram and thrashing

		if saturated:
			reason = "Low available RAM + high paging — memory bottleneck"
		elif commit_risk:
			reason = "Commit charge near limit — risk of OOM"
		elif low_ram:
			reason = "Low available RAM but low paging — compression coping"
		elif thrashing:
			reason = "High paging but RAM not critically low — check app behavior"
		else:
			reason = "Memory healthy"

		return {
			"saturated": saturated,
			"available_mb": avail,
			"pages_per_sec": pages,
			"commit_pct": commit,
			"reason": reason,
		}

	def close(self):
		for hc in (getattr(self, "_hc_avail", None),
				getattr(self, "_hc_pages", None),
				getattr(self, "_hc_commit", None)):
			if hc is not None:
				try:
					win32pdh.RemoveCounter(hc)
				except Exception:
					pass
		self._hc_avail = self._hc_pages = self._hc_commit = None
		if getattr(self, "_hq", None) is not None:
			try:
				win32pdh.CloseQuery(self._hq)
			except Exception:
				pass
		self._hq = None

	def __enter__(self):
		return self

	def __exit__(self, *exc_info):
		self.close()

	def __del__(self):
		self.close()