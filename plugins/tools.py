﻿import sys
import os
import time
import datetime
import threading
from multiprocessing.dummy import Pool as ThreadPool
import re
import winsound
import glob
import ctypes
import sqlite3
import pyperclip
import random
import functools
import string
import win32api
import win32gui
import win32con
import wx


APP_NAME = 'Taskopy'
APP_VERSION = 'v2020-02-09'
APP_FULLNAME = APP_NAME + ' ' + APP_VERSION

app_log = []

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
	, ['http_dir', None]
	, ['err_threshold', 0]
	, ['err_counter', False]
	, ['no_print', False]
	, ['idle', None]
	, ['on_load', False]
	, ['rule', None]
	, ['thread', None]
	, ['last_start', None]
]

APP_SETTINGS=[
	['dev', False]
	, ['language', 'en']
	, ['menu_hotkey', None]
	, ['editor', 'notepad.exe']
	, ['server_ip', '127.0.0.1']
	, ['server_port', 8275]
	, ['white_list', '127.0.0.1']
	, ['server_silent', True]
	, ['hide_console', False]
	, ['kiosk', False]
	, ['kiosk_key', 'shift']
	, ['log_file_name', '%Y.%m.%d']
]

_DEFAULT_INI = '''[General]
language=en
editor=notepad.exe
hide_console=False

[HTTP]
server_ip=127.0.0.1
server_port=80
white_list=127.0.0.1
'''

if getattr(sys, 'frozen', False):
	_APP_PATH = os.path.dirname(sys.executable)
else:
	_APP_PATH = os.getcwd()

_DB_FILE = _APP_PATH + r'\resources\db.sqlite3'
_TIME_UNITS = {'msec':1, 'ms':1, 'sec':1000, 's':1000, 'min':60000
				,'m':60000, 'hour':3600000, 'h':3600000}

class DictToObj:
	''' Converts dictionary to object.
		Convert back: use vars() built-in function.
	'''
	def __init__(s, di:dict):
		s.__dict__.update(di)

	def __getattr__(s, name):
		return 'DictToObj - unknown key'

def value_unit(value, unit_dict:dict, default:int)->tuple:
	''' Returns (int, int) - value and coefficient found in unit_dict.
		If no unit is found, it returns the default value.
	'''


	if isinstance(value, int):
		return value, default
	elif value.isdigit():
		return int(value), default
	elif ' ' in value:
		v, u = value.split()
		return int(v), unit_dict.get(u, default)
	elif any(i.isdigit() for i in value):
		v = ''.join(filter(str.isdigit, value))
		return int(v), unit_dict.get(value.replace(v, ''), default)
	else:
		dev_print(f'value_unit wrong value: {value}')
		return value, default

def task(**kwargs):
	def with_attrs(func):
		for key, value in kwargs.items():
			setattr(func, key, value)
		setattr(func, 'is_task', True)
		return func
	return with_attrs

def sound_play(fullpath, wait=False):
	''' Play .wav sound. If fullpath is a folder then pick random file.
	'''
	if os.path.isdir(fullpath):
		fi = random.choice(glob.glob(fullpath + '\\*'))
	else:
		fi = fullpath
	if wait:
		winsound.PlaySound(fi, winsound.SND_FILENAME)
	else:
		winsound.PlaySound(fi, winsound.SND_FILENAME + winsound.SND_ASYNC)

def dev_print(*msg, **kwargs):
	d = False
	if getattr(__builtins__, 'sett', None):
		d = sett.dev
	else:
		d = True
	if d: tprint(*msg, **kwargs)

def con_log(*msgs):
	''' Log to console and logfile
	'''
	global app_log
	log_str = ''
	for m in msgs:
		tprint(m)
		app_log.append((datetime.datetime.now(), m))
		log_str += (
			time.strftime('%Y.%m.%d %H:%M:%S')
			+ ' ' + str(m) + '\n'
		)
	try:
		with open(
			f'log\\{time.strftime(sett.log_file_name)}.log'
			, 'ta+', encoding='utf-8'
		) as f:
			f.write(log_str)
	except FileNotFoundError:
		os.makedirs('log')
		with open(
			f'log\\{time.strftime(sett.log_file_name)}.log'
			, 'ta+', encoding='utf-8'
		) as f:
			f.write(log_str)

def time_now(template:str='%Y-%m-%d_%H-%M-%S'):
	return time.strftime(template)

def time_hour()->int:
	'''Returns current hour'''
	return datetime.datetime.now().hour

def time_minute()->int:
	'''Returns current minute'''
	return datetime.datetime.now().minute

def time_second()->int:
	'''Returns current second'''
	return datetime.datetime.now().second

def date_year()->int:
	'''Returns current year'''
	return datetime.datetime.now().year

def date_month()->int:
	'''Returns current month'''
	return datetime.datetime.now().month

def date_day()->int:
	'''Returns current day'''
	return datetime.datetime.now().day

def date_weekday(tdate=None, template:str='%A')->str:
	''' tdate may be datetime.date(2019, 6, 12)
	'''
	if not tdate: tdate = datetime.date.today()
	return tdate.strftime(template)

def time_sleep(interval):
	''' Pauses for specified amount of time.
		interval - int of seconds or str with unit like '5 min'
	'''
	val, coef = value_unit(interval, _TIME_UNITS, 1000)
	time.sleep(val * coef / 1000)
pause = time_sleep
wait = time_sleep

def db_execute(sql:str):
	''' Execute sql in _DB_FILE
	'''
	conn = sqlite3.connect(_DB_FILE)
	cur = conn.cursor()
	cur.execute(sql)
	conn.commit()
	conn.close()

def _create_table_var():
	db_execute('''CREATE TABLE variables
				(vname TEXT PRIMARY KEY, vvalue TEXT)''')

def var_set(var_name:str, value:str):
	''' Store variable value in db.sqlite3 in table "variables"
		It needs sqlite version 3.24+ (just replace dll)
	'''
	value = str(value).replace("'", "''")
	try:
		conn = sqlite3.connect(_DB_FILE)
		cur = conn.cursor()
		cur.execute(f'''INSERT INTO variables (vname, vvalue)
						VALUES('{var_name}', '{value}')
						ON CONFLICT(vname)
						DO UPDATE SET vvalue=excluded.vvalue;
					''')
		conn.commit()
	except sqlite3.OperationalError:
		if sett.dev: raise
		_create_table_var()
		cur.execute(f'''INSERT INTO variables (vname, vvalue)
						VALUES('{var_name}', '{value}')
						ON CONFLICT(vname)
						DO UPDATE SET vvalue=excluded.vvalue;
					''')
		conn.commit()
	conn.close()

def var_get(var_name:str, table:str='variables')->str:
	''' Retrieves value from db.sqlite3 and returns '' if 
		there is none.
	'''
	try:
		conn = sqlite3.connect(_DB_FILE)
		cur = conn.cursor()
		cur.execute(
			f'''SELECT vvalue
				FROM {table}
				WHERE vname = '{var_name}'
			'''
		)
		r = cur.fetchone()
		if r:
			r = r[0]
		else:
			r = ''
	except sqlite3.OperationalError:
		_create_table_var()
		r = ''
	conn.close()
	return r

def clip_set(txt:str):
	pyperclip.copy(txt)

def clip_get()->str:
	return pyperclip.paste()

def re_find(source:str, re_pattern:str, sort:bool=False
, unique:bool=True, re_flags:int=re.IGNORECASE)->list:
	r''' Return list with matches.
		re_flags:
			re.IGNORECASE	ignore case
			re.MULTILINE	make begin/end {^, $} consider each line.
			re.DOTALL	make . match newline too.
			re.UNICODE	make {\w, \W, \b, \B} follow Unicode rules.
			re.LOCALE	make {\w, \W, \b, \B} follow locale.
			re.VERBOSE	allow comment in regex.
		Non-capturing group: (?:aaa)
	'''
	matches = re.findall(re_pattern, source, flags=re_flags)
	if unique: matches = list(set(matches))
	if sort: matches.sort()
	return matches

def re_replace(source:str, re_pattern:str, repl:str=''
, re_flags:int=re.IGNORECASE)->str:
	''' Regexp replace substring'''
	r = re.sub(
		pattern=re_pattern
		, repl=repl
		, string=source
		, flags=re_flags
	)
	return r

def re_match(source:str, re_pattern:str
, re_flags:int=re.IGNORECASE)->bool:
	''' Regexp match '''
	return bool(re.match(re_pattern, source, flags=re_flags))

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

def msgbox(msg:str, title:str=None
, ui:int=None, wait:bool=True, timeout=None
	, dis_timeout:float=None)->int:
	''' wait - msgbox should be closed to continue task
		ui - combination of buttons and icons
		timeout - timeout in seconds (int) or str with
			unit: '5 sec', '5 min', '2 hour' etc
		dis_timeout (seconds) - disable buttons for x seconds.
			Should be smaller than timeout.
	'''
	def get_hwnd(title_tmp:str):
		hwnd = 0
		for _ in range(1000):
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
	if title:
		title = str(title)
	else:
		title = sys._getframe(1).f_code.co_name.replace('_', ' ')
		if title.startswith('<'): title = APP_NAME
	if ui: ui += MB_SYSTEMMODAL
	else:
		ui = MB_ICONINFORMATION + MB_SYSTEMMODAL
	if timeout:
		mb_func = _MessageBoxTimeout
		title_tmp = title + '          rand' + str(random.randint(100000, 1000000))
		value, coef = value_unit(timeout, _TIME_UNITS, 1000)
		timeout = int(value * coef / 1000)
		mb_args = (None, msg, title_tmp, ui, 0, timeout * 1000)
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
		if timeout:
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
					threading.Thread(
						target=title_countdown
						, args=(hwnd, timeout, title)
						, daemon=True
					).start()
			else:
				threading.Thread(
					target=mb_func
					, args=mb_args
					, daemon=True
				).start()
				hwnd = get_hwnd(title_tmp)
				if hwnd:
					win32gui.SetWindowText(hwnd, title)
					threading.Thread(
						target=title_countdown
						, args=(hwnd, timeout, title,)
						, daemon=True
					).start()
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
	msgbox(msg=msg, title=APP_NAME, ui=MB_ICONWARNING, wait=False)

def inputbox(message:str, title:str=None
, is_pwd:bool=False, default:str='', multiline:bool=False)->str:
	''' Request input from user.
		is_pwd - use password dialog (hide input).
		Problem: don't use default or you will get it value
		whatever button user will press.
	'''
	if not title:
		title = sys._getframe(1).f_code.co_name.replace('_', ' ')
		if title.startswith('<'): title = APP_NAME
	if is_pwd:
		box_func = wx.PasswordEntryDialog
	else:
		box_func = wx.TextEntryDialog
	style=(wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP)
	if multiline: style += wx.TE_MULTILINE
	dlg = box_func(app.frame, message, title, style=style)
	win32gui.SetWindowPos(
		dlg.Handle
		, win32con.HWND_TOPMOST
		, 0, 0, 0, 0
		, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE
	)
	if default: dlg.SetValue(default)
	try:
		win32gui.SetForegroundWindow(dlg.Handle)
	except:
		pass
	try:
		dlg.ShowModal()
	except wx._core.wxAssertionError: 	
		pass
	value = dlg.GetValue()
	dlg.Destroy()
	return value

def file_dialog(title:str=None, multiple:bool=False
, default_dir:str='', default_file:str=''
, wildcard:str='', on_top:bool=True):
	''' Shows standard file dialog
		and returns fullpath or list of fullpaths
		if multiple == True.
		Will not work in console.
	'''
	if not title:
		title = sys._getframe(1).f_code.co_name.replace('_', ' ')
		if title.startswith('<'): title = APP_NAME
	style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
	if multiple: style = style | wx.FD_MULTIPLE
	if on_top: style = style | wx.STAY_ON_TOP
	dialog = wx.FileDialog(None, title, wildcard=wildcard
		, defaultDir=default_dir, defaultFile=default_file, style=style)
	if dialog.ShowModal() == wx.ID_OK:
		if multiple:
			fullpath = dialog.GetPaths()
		else:
			fullpath = dialog.GetPath()
	else:
		fullpath = None
	dialog.Destroy()
	return fullpath

random_num = random.randint

def random_str(string_len:int=10, string_source:str=None)->str:
	''' Generate a random string of fixed length
	'''
	if not string_source: string_source = string.ascii_letters + string.digits
	return ''.join(random.choice(string_source) for i in range(string_len))

def app_icon_text_set(text:str=APP_FULLNAME):
	''' Set hint text for taskbar icon.
	'''
	app.taskbaricon.set_icon(text=text)

def create_default_ini_file():
	''' Creates default settings.ini file.
	'''
	with open('settings.ini', 'xt', encoding='utf-8-sig') as ini:
		ini.write(_DEFAULT_INI)

def jobs_pool(function:str, args:tuple, pool_size:int=None)->list:
	''' Launches 'pool_size' functions at a time for
		all the 'args'. Returns list of results.
		'args' may be a tuple of tuples or tuple of values.
		If 'pool_size' not specified, pool_size = number of CPU.
		Example:
			jobs_pool(
				msgbox
				, (
					'one'
					, 'two'
					, 'three'
					, 'four'
				)
				, 4
			)
	'''
	pool = ThreadPool(pool_size)
	if isinstance(args[0], (tuple, list, dict)):
		map_func = pool.starmap
	else:
		map_func = pool.map
	results = map_func(function, args)
	pool.close()
	pool.join()
	return results

def jobs_batch(func_list:list, timeout:int
, sleep_timeout:float=0.001)->list:
	''' Runs functions (they may not be same) in threads and waits
		when all of them return result or timeout is expired.
		func_list - list of sublist, where sublist should consist of 3
		items: function, (args), {kwargs}.
		Returns list of job objects, where job have these attributes:
		func, args, kwargs, result, time
		Example:
		func_list = [
			[function1, (1, 3, 4), {'par1': 2, 'par2':3}]
			, [function2, (), {'par1':'foo', 'par2':'bar'}]
			...
		]
		jobs:
		[
			<job.func=function1, job.args = (1, 3, 4), job.kwargs={'par1': 2, 'par2':3}
				, job.result=True, job.time='0:00:00.0181'>
			, <job.func=function2, job.args = (), job.kwargs={'par1':'foo', 'par2':'bar'}
				, job.result=[True, data], job.time='0:00:05.827'>

			...
		]
	'''
	jobs = []
	time_start = time.time()
	for li in func_list:
		job = {}
		job['func'] = li[0]
		if len(li) > 1:
			if isinstance(li[1], (list, tuple)):
				job['args'] = li[1]
			else:
				job['args'] = [li[1]]
		else:
			job['args'] = []
		if len(li) > 2:
			job['kwargs'] = li[2]
		else:
			job['kwargs'] = {}
		job['result'] = []
		job['time'] = None
		jobs.append(job)
		threading.Thread(
			target=lambda *a, **kw: job['result'].extend([
				job['func'](*a, **kw)
				, datetime.timedelta(seconds=(time.time() - time_start))
			])
			, args=job['args']
			, kwargs=job['kwargs']
			, daemon=True
		).start()
	for _ in range(int(timeout / sleep_timeout)):
		if all([len(j['result'])==2 for j in jobs]):
			for job in jobs:
				job['result'], job['time'] = job['result']
			return [DictToObj(j) for j in jobs]
		time.sleep(sleep_timeout)
	else:
		for job in jobs:
			if len(job['result']):
				job['result'], job['time'] = job['result']
			else:
				job['result'] = 'timeout'
				job['time'] = 'timeout'
		return [DictToObj(j) for j in jobs]

def tprint(*msgs, **kwargs):
	''' Print with task name and time '''
	parent = sys._getframe(1).f_code.co_name
	msgs = list(msgs)
	if not parent in ['dev_print', 'con_log']:
		msgs.insert(0, parent + ':')
	print(time.strftime('%y.%m.%d %H:%M:%S'), *msgs, **kwargs)

def balloon(msg:str, title:str=APP_NAME, timeout:int=None, icon:str=None):
	''' Show balloon. title - 63 symbols max, msg - 255.
		icon - 'info', 'warning' or 'error'.
	'''
	kwargs = {'title': title, 'text': msg}
	if timeout: kwargs['msec'] = timeout * 1000
	if icon:
		kwargs['flags'] = {
			'info': wx.ICON_INFORMATION
			, 'error': wx.ICON_ERROR
			, 'warning': wx.ICON_WARNING
		}.get(icon.lower(), wx.ICON_INFORMATION)
	app.taskbaricon.ShowBalloon(**kwargs)

def app_log_get():
	''' Returns current log file content.
		Log can't be empty.
	'''
	log = ''
	for t, m in app_log:
		log += t.strftime('%Y.%m.%d %H:%M:%S') + f'\t{m}\n'
	return log




def decor_except(func):
	''' Make try... except for function
		and return Exception object on fail.

		Downside - iPython autoreload does not
		work for decorated 'func'.
	'''
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		try:
			result = func(*args, **kwargs)
			return result
		except Exception as e:
			if getattr(__builtins__, 'sett', None):
				if sett.dev:
					print(f'decor_except exception: {func} {repr(e)}')
			return e
	return wrapper
