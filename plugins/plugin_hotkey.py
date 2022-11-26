import ctypes
import ctypes.wintypes
import win32con
import keyboard
try:
	from .tools import warning, patch_import, time_sleep, tdebug
except ImportError:
	warning = print

# Key codes https://docs.microsoft.com/en-us/windows/desktop/inputdev/virtual-key-codes
# https://github.com/boppreh/keyboard

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

class GlobalHotKeys():
	''' Register a global hotkey using the register() method.
		Start the listening mode with 'listen' method which
		SHALL be run in another thread.
	'''
	
	def __init__(s):
		s.thread_id = 0
		s.key_mapping = []
		s.keys = {}
		s.modifiers = {
			'alt': win32con.MOD_ALT
			, 'ctrl': win32con.MOD_CONTROL
			, 'shift': win32con.MOD_SHIFT
			, 'win': win32con.MOD_WIN
		}
		s.fill_key_dict()

	def fill_key_dict(s):
		''' Fill keys dict with VK_ constants from win32con
		'''
		for item, value in win32con.__dict__.items():
			if str(item)[:3] == 'VK_':
				s.keys[str(item[3:]).lower()] = value
		for key_code in (
			list(range(ord('A'), ord('Z') + 1))
			+ list(range(ord('0'), ord('9') + 1))
		):
			s.keys[chr(key_code).lower()] = key_code

	def register(s, hotkey:str, func=None, func_args:list=[]):
		''' hotkey - string like 'ctrl+shift+m'
			func - function to run on hotkey
			func_args - list of arguments for func
		'''
		modifier = 0
		key_li = hotkey.lower().split('+')
		if len(key_li) > 1:
			for k in key_li:
				if k in s.modifiers.keys():
					modifier |= s.modifiers[k]
				elif k in s.keys.keys():
					vk = s.keys[k]
				elif k.isdigit():
					vk = int(k)
				else:
					raise Exception(f'Unknown key: {k}')
		else:
			k = key_li[0]
			vk = s.keys.get(k)
			if not vk:
				if k.isdigit():
					vk = int(k)
				else:
					raise Exception(f'Unknown key: {k}')
 
		s.key_mapping.append(
			(vk, modifier, lambda a=func_args: func(*a))
		)

	def stop_listener(s):
		''' Stop current listen thread
		'''
		WM_QUIT = 0x0012
		_user32.PostThreadMessageW(s.thread_id, WM_QUIT, 0, 0)

	def unregister(s):
		for index, (vk, modifiers, func) in enumerate(s.key_mapping):
			_user32.UnregisterHotKey(None, index)

	def listen(s):
		''' Start listening for hotkeys
		'''
		s.thread_id = _kernel32.GetCurrentThreadId()
		for index, (vk, modifiers, func) in enumerate(s.key_mapping):
			if not _user32.RegisterHotKey(None, index, modifiers, vk):
				error = (
					'Unable to register hot key: '
					+ str(vk) + ' error code is: '
					+ str(_kernel32.GetLastError())
				)

				print(error)
				warning(error)
 
		try:
			msg = ctypes.wintypes.MSG()
			while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
				if msg.message == win32con.WM_HOTKEY:
					(vk, modifiers, func) = s.key_mapping[msg.wParam]
					if not func:
						break
					func()
				_user32.TranslateMessage(ctypes.byref(msg))
				_user32.DispatchMessageA(ctypes.byref(msg))
		finally:
			s.unregister()
key_pressed = keyboard.is_pressed
key_send = keyboard.send
key_write = keyboard.write

key_press = keyboard.press
key_release = keyboard.release

def key_release_wait(keys:str, timeout='10 ms'):
	'''
	Wait until all the keys are released.
	*keys* - a string with hotkey for a task like 'ctrl+shift+m'
	Use this if you want to send keystrokes by hotkey.
	'''
	while True:
		if any( map( keyboard.is_pressed, keys.split('+') ) ):
			time_sleep(timeout)
		else:
			break
		


if __name__ == '__main__':
	''' Test this module: bind test_func to 'ctrl+t'
		global hotkey and exit test with 'ctrl+shift+t'
	'''
	import threading
	def test_func(t:str='no arg'):
		print(t)
	
	ghk = GlobalHotKeys()
	ghk.register(
		'ctrl+t', func=test_func, func_args=['test passed']
	)
	ghk.register('ctrl+shift+t', func=ghk.stop_listener)
	print('Hotkey test: press ctrl+t')
	threading.Thread(target=ghk.listen).start()
else:
	patch_import()