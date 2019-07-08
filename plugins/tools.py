import os
import time
import datetime
import threading
import re
import winsound
import ctypes
import sqlite3
import pyperclip
import random
import win32api
import win32gui
from .plugin_send_mail import send_email

APP_NAME = 'Taskopy'
APP_VERSION = 'v2019-07-08'
APP_FULLNAME = APP_NAME + ' ' + APP_VERSION

TASK_OPTIONS = [
	['task_name', None]
	, ['task', True]
	, ['menu', True]
	, ['hotkey', None]
	, ['hotkey_suppress', True]
	, ['schedule', None]
	, ['active', True]
	, ['startup', False]
	, ['sys_startup', False]
	, ['left_click', False]
	, ['log', True]
	, ['single', True]
	, ['running', False]
	, ['submenu', None]
	, ['result', False]
	, ['http', False]
]

APP_SETTINGS=[
	['developer', False]
	, ['language', 'en']
	, ['menu_hotkey', None]
	, ['editor', 'notepad.exe']
	, ['server_ip', '127.0.0.1']
	, ['server_port', 80]
	, ['server_silent', True]
]

DB_FILE = (
	os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	+ r'\resources\db.sqlite3'
)

def task(**kwargs):
	def with_attrs(func):
		for key, value in kwargs.items():
			setattr(func, key, value)
		setattr(func, 'is_task', True)
		return func
	return with_attrs

def sound_play(fullpath, wait=False):
	if wait:
		winsound.PlaySound(fullpath, winsound.SND_FILENAME)
	else:
		winsound.PlaySound(fullpath, winsound.SND_FILENAME + winsound.SND_ASYNC)

def con_log(msg:str, log_file:bool=True):
	''' Log to console and logfile
	'''
	msg = f"{time.strftime('%y.%m.%d %H:%M:%S')} {msg}"
	print(msg)
	if not log_file: return
	with open(
		f"log\\{time.strftime('%y.%m.%d')}.txt"
		, 'ta+', encoding='utf-8'
	) as f:
		f.write(msg + '\n')

def time_now(template:str='%Y-%m-%d_%H-%M-%S'):
	return time.strftime(template)

def time_weekday(tdate=None, template:str='%A')->str:
	''' tdate may be datetime.date(2019, 6, 12)
	'''
	if not tdate: tdate = datetime.date.today()
	return tdate.strftime(template)

def time_sleep(sec:float):
	time.sleep(sec)

def db_execute(sql:str):
	''' Execute sql in DB_FILE '''
	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()
	cur.execute(sql)
	conn.commit()
	conn.close()

def _create_new_db():
	db_execute('''CREATE TABLE variables
				(vname TEXT PRIMARY KEY, vvalue TEXT)''')

def var_set(var_name:str, value:str):
	''' Store variable value in db.sqlite3 in table "variables"
		It needs sqlite version 3.24+ (just replace dll)
	'''
	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()
	cur.execute(f'''INSERT INTO variables (vname, vvalue)
					VALUES('{var_name}', '{value}')
					ON CONFLICT(vname)
					DO UPDATE SET vvalue=excluded.vvalue;
				''')
	conn.commit()
	conn.close()

def var_get(var_name:str)->str:
	''' Retrieves variable from db.sqlite3 and returns '' if 
		there is none
	'''
	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()
	cur.execute(f'''SELECT vvalue
					FROM variables
					WHERE vname = '{var_name}'
				''')
	r = cur.fetchone()
	if r:
		r = r[0]
	else:
		r = ''
	conn.close()
	return r

def clip_set(txt:str):
	pyperclip.copy(txt)

def clip_get()->str:
	return pyperclip.paste()

def re_find(source:str, re_pattern:str, sort:bool=True
	, re_flags:int=re.IGNORECASE)->list:
	''' Return list with matches.
		re_flags:
			re.IGNORECASE	ignore case
			re.MULTILINE	make begin/end {^, $} consider each line.
			re.DOTALL	make . match newline too.
			re.UNICODE	make {\w, \W, \b, \B} follow Unicode rules.
			re.LOCALE	make {\w, \W, \b, \B} follow locale.
			re.VERBOSE	allow comment in regex.
	'''
	matches = list(
		set(
			re.findall(re_pattern, source, flags=re_flags)
		)
	)
	if sort: matches.sort()
	return matches

def re_replace(source:str, re_pattern:str, repl:str=''
				, re_flags:int=re.IGNORECASE)->str:
	r = re.sub(
		pattern=re_pattern
		, repl=repl
		, string=source
		, flags=re_flags
	)
	return r

def email_send(
		recipient:str
		, subject:str
		, message:str
		, smtp_server:str
		, smtp_port:int
		, smtp_user:str
		, smtp_password:str
	):
	''' Send email
	'''
	send_email(
		receiver_email=recipient
		, subject=subject
		, from_name=APP_NAME
		, message=message
		, smtp_server=smtp_server
		, smtp_port=smtp_port
		, smtp_user=smtp_user
		, smtp_password=smtp_password
	)
	
_MessageBox = ctypes.windll.user32.MessageBoxW
_MessageBoxTimeout = ctypes.windll.user32.MessageBoxTimeoutW
MB_ABORTRETRYIGNORE = 0x00000002
MB_CANCELTRYCONTINUE = 0x00000006
MB_HELP = 0x00004000
MB_OK = 0x00000000
MB_OKCANCEL = 0x00000001
MB_RETRYCANCEL = 0x00000005
MB_YESNO =0x00000004
MB_YESNOCANCEL = 0x00000003

MB_DEFBUTTON1 = 0x00000000
MB_DEFBUTTON2 = 0x00000100
MB_DEFBUTTON3 = 0x00000200
MB_DEFBUTTON4 = 0x00000300

MB_ICONEXCLAMATION = 0x00000030
MB_ICONWARNING = 0x00000030
MB_ICONINFORMATION = 0x00000040
MB_ICONASTERISK = 0x00000040
MB_ICONQUESTION = 0x00000020
MB_ICONSTOP = 0x00000010
MB_ICONERROR = 0x00000010
MB_ICONHAND = 0x00000010

MB_APPLMODAL = 0x00000000
MB_SYSTEMMODAL = 0x00001000
MB_TASKMODAL = 0x00002000

MB_RIGHT = 0x00080000
MB_RTLREADING = 0x00100000
MB_SETFOREGROUND = 0x00010000
MB_TOPMOST = 0x00040000

IDABORT = 3
IDCANCEL = 2
IDCONTINUE = 11
IDIGNORE = 5
IDNO = 7
IDOK = 1
IDRETRY = 4
IDTRYAGAIN = 10
IDYES = 6

def msgbox(msg:str, title:str=APP_NAME
	, ui:int=None, wait:bool=True, timeout:int=None
	, dis_timeout:float=None)->int:
	''' wait - msgbox should be closed to continue task
		ui - combination of buttons and icons
		timeout - timeout in seconds
		dis_timeout (seconds) - disable buttons for x seconds.
			Should be smaller than timeout.
	'''
	def get_hwnd(title_tmp:str):
		hwnd = 0
		for i in range(1000):
			hwnd = win32gui.FindWindow(None, title_tmp)
			if hwnd:
				break
		return hwnd
	
	def title_countdown(hwnd:int, timeout:int, title:str):
		for sec in reversed(range(100 * timeout ) ):
			try:
				win32gui.SetWindowText(
					hwnd
					, f'[{sec // 100 + 1}] {title}'
				)
			except:
				break
			time.sleep(0.01)
	
	def dis_buttons(hwnd:int, dis_timeout:float):
		def dis_butt(hchild, state):
			
			if win32gui.GetWindowLong(hchild, -12) < 12:
				win32gui.ShowWindow(hchild, state)
			return True
		
		time.sleep(0.01)
		try:
			win32gui.EnumChildWindows(hwnd, dis_butt, False)
			time.sleep(dis_timeout)
			win32gui.EnumChildWindows(hwnd, dis_butt, True)
		except:
			pass
		
	if ui:
		ui += MB_SYSTEMMODAL
	else:
		ui = MB_ICONINFORMATION + MB_SYSTEMMODAL
	if timeout:
		mb_func = _MessageBoxTimeout
		title_tmp = title + '          rand' + str(random.randint(100000, 1000000))
		mb_args = (None, msg, title_tmp, ui, 0, timeout*1000)
	else:
		if dis_timeout:
			mb_func = _MessageBox
			title_tmp = title + '          rand' + str(random.randint(100000, 1000000))
			mb_args = (None, msg, title_tmp, ui)
		else:
			mb_func = _MessageBox
			mb_args = (None, msg, title, ui)
	if wait:
		if timeout:
			result = []
			threading.Thread(
				target=lambda *a, r=result: r.append(mb_func(*a))
				, args=mb_args
				, daemon=True
			).start()
			hwnd = get_hwnd(title_tmp)
			if hwnd:
				if dis_timeout:
					threading.Thread(
						target=dis_buttons
						, args=(hwnd, dis_timeout,)
						, daemon=True
					).start()
				threading.Thread(
					target=title_countdown
					, args=(hwnd, timeout, title,)
					, daemon=True
				).start()
			while not result: time.sleep(0.01)
			if result:
				return result[0]
			else:
				return 0
		else:
			if dis_timeout:
				result = []
				threading.Thread(
					target=lambda *a, r=result: r.append(mb_func(*a))
					, args=mb_args
					, daemon=True
				).start()
				hwnd = get_hwnd(title_tmp)
				if hwnd:
					win32gui.SetWindowText(hwnd, title)
					threading.Thread(
						target=dis_buttons
						, args=(hwnd, dis_timeout,)
						, daemon=True
					).start()
				while not result: time.sleep(0.01)
				return result[0]
			else:
				return mb_func(*mb_args)
	else:
		if dis_timeout:
			threading.Thread(
				target=mb_func
				, args=mb_args
				, daemon=True
			).start()
			hwnd = get_hwnd(title_tmp)
			if hwnd:
				win32gui.SetWindowText(hwnd, title)
				threading.Thread(
					target=dis_buttons
					, args=(hwnd, dis_timeout,)
					, daemon=True
				).start()
		else:
			threading.Thread(
				target=mb_func
				, args=mb_args
				, daemon=True
			).start()

def msgbox_warning(msg:str):
	msgbox(msg, APP_NAME, MB_ICONWARNING)
