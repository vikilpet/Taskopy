import ctypes
import ctypes.wintypes
import win32con
import keyboard
from collections import namedtuple
try:
	from .tools import warning, patch_import, time_sleep, qprint
except ImportError:
	warning = print

r'''
Key codes: https://docs.microsoft.com/en-us/windows/desktop/inputdev/virtual-key-codes
https://github.com/boppreh/keyboard

Key codes for task option *hotkey* (windows VK) and for *key_* (keyboard module)
functions not always the same!  

	from keyboard._canonical_names import canonical_names
	sorted(set(canonical_names.values()))

Special keys for *keyboard* module:

	'comma',
	'plus',
	'space',
	'alt',
	'alt gr',
	'backspace',
	'caps lock',
	'ctrl',
	'delete',
	'down',
	'enter',
	'esc',
	'insert',
	'left',
	'left alt',
	'left ctrl',
	'left windows',
	'menu',
	'num lock',
	'page down',
	'page up',
	'pause',
	'play/pause media',
	'print screen',
	'right',
	'right ctrl',
	'right windows',
	'scroll lock',
	'tab',
	'up',
	'windows',
	'volume_up',
	'voume_down'

How to find a key name (exit on *space*):

	while True:
		keyboard_event = keyboard.read_event(True)
		print(keyboard_event.event_type, keyboard_event.name)
		if keyboard_event.name == 'space': break

'''

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_KeyMap = namedtuple('KeyMap', ('vkey', 'modifier', 'func', 'args'))

class GlobalHotKeys:
	r'''
	Register a global hotkey using the register() method.  
	Start the listening mode with *listen* method which 
	SHALL run in a different thread.  
	'''

	def __init__(self):
		self.thread_id:int = 0
		self.key_mapping:list = []
		self.keys:dict = {}
		self.modifiers:dict = {
			'alt': win32con.MOD_ALT
			, 'ctrl': win32con.MOD_CONTROL
			, 'shift': win32con.MOD_SHIFT
			, 'win': win32con.MOD_WIN
		}
		self.fill_key_dict()

	def fill_key_dict(self):
		r'''
		Fill keys dict with *VK_* constants from `win32con`
		'''
		for item, value in win32con.__dict__.items():
			if str(item)[:3] == 'VK_':
				self.keys[str(item[3:]).lower()] = value
		for key_code in (
			list(range(ord('A'), ord('Z') + 1))
			+ list(range(ord('0'), ord('9') + 1))
		):
			self.keys[chr(key_code).lower()] = key_code

	def register(self, hotkey:str, func=None, func_args:list=[]):
		r'''
		*hotkey* - string like 'ctrl+shift+m'  
		*func* - function to run on hotkey  
		*func_args* - list of arguments for func  
		'''
		vkey:int = 0
		modifier:int = 0
		key_li = [k.strip() for k in hotkey.strip().lower().split('+')]
		if len(key_li) > 1:
			for key in key_li:
				if key in self.modifiers.keys():
					modifier |= self.modifiers[key]
				elif key in self.keys.keys():
					vkey = self.keys[key]
				elif key.isdigit():
					vkey = int(key)
				else:
					raise Exception(f'Unknown key: {key}')
		else:
			key = key_li[0]
			vkey = self.keys.get(key, 0)
			if not vkey:
				if key.isdigit():
					vkey = int(key)
				else:
					raise Exception(f'Unknown key: {key}')
 
		self.key_mapping.append(_KeyMap(vkey=vkey, modifier=modifier
		, func=func, args=func_args))

	def stop_listener(self):
		r'''
		Stop the current listening thread.
		'''
		WM_QUIT = 0x0012
		_user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)

	def unregister(self):
		for index, _ in enumerate(self.key_mapping):
			_user32.UnregisterHotKey(None, index)

	def listen(self):
		r'''
		Start listening for hotkeys.
		'''
		self.thread_id = _kernel32.GetCurrentThreadId()
		kmap:_KeyMap
		for index, kmap in enumerate(self.key_mapping):
			if not _user32.RegisterHotKey(None, index, kmap.modifier
			, kmap.vkey):
				lasterr = _kernel32.GetLastError()
				if lasterr == 1409: lasterr = 'hotkey is already registered'
				error = (
					'Task: «' + kmap.args[0].get('task_name_full', '?') + '»'
					+ '\nHotkey: ' + kmap.args[0].get('hotkey', '??')
					+ f' ({kmap.vkey})'
					+ f'\nHotkey register error: {lasterr}'
				)
				qprint(error)
				warning(error)
		try:
			msg = ctypes.wintypes.MSG()
			while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
				if msg.message == win32con.WM_HOTKEY:
					kmap = self.key_mapping[msg.wParam]
					if not kmap.func: break
					kmap.func(*kmap.args)
				_user32.TranslateMessage(ctypes.byref(msg))
				_user32.DispatchMessageA(ctypes.byref(msg))
		finally:
			self.unregister()
key_pressed = keyboard.is_pressed
key_send = keyboard.send
key_write = keyboard.write

key_press = keyboard.press
key_release = keyboard.release
key_wait = keyboard.wait

def key_release_wait(keys:str, timeout='10 ms'):
	r'''
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
	r'''
	Test this module: bind test_func to 'ctrl+t' global hotkey
	and exit test with 'ctrl+shift+t'
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