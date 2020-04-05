import sys
import os
import time
import datetime
import threading
from multiprocessing.dummy import Pool as ThreadPool
import re
import winsound
import glob
import traceback
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
APP_VERSION = 'v2020-04-05'
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
	, 'm':60_000, 'hour':3_600_000, 'h':3_600_000, 'day': 86_400_000
	, 'd': 86_400_000}

class DictToObj:
	''' Converts dictionary to object.
		Convert back: use vars() built-in function.
	'''
	def __init__(s, di:dict):
		s.__dict__.update(di)

	def __getattr__(s, name):
		return 'DictToObj - unknown key'

def value_unit(value, unit_dict:dict, default:int)->tuple:
	''' Returns (int, int) - value and coefficient
		found in unit_dict.
		If no unit is found, it returns the 'default' value.
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

def _get_parent_func_name(title)->str:
	''' Get name of parent function if any '''
	if title: return str(title)
	title = sys._getframe(2).f_code.co_name.replace('_', ' ')
	if title.startswith('<'): title = APP_NAME
	return title

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

def time_now_str(template:str='%Y-%m-%d_%H-%M-%S'):
	'String with time'
	return time.strftime(template)

def time_now():
	'Returns datetime object'
	return datetime.datetime.now()

def time_hour()->int:
	'''Returns current hour'''
	return datetime.datetime.now().hour

def time_minute()->int:
	'''Returns current minute'''
	return datetime.datetime.now().minute

def time_second()->int:
	'''Returns current second'''
	return datetime.datetime.now().second

def time_diff(start, end, unit:str='sec')->int:
	'''	Returns difference in units.
		start and end should be in datetime format.
	'''
	seconds = (end - start).total_seconds()
	coef = _TIME_UNITS.get(unit, 1000) / 1000
	return int(seconds // coef)

def time_diff_str(start, end)->str:
	'''	Returns time difference in string like that:
		'3:01:35'
		start and end should be in datetime format.
	'''
	return str(end - start)
	

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

def date_weekday_num(tdate=None, template:str='%A')->str:
	''' Weekday number (Monday is 0).
		tdate may be datetime.date(2019, 6, 12)
	'''
	if not tdate: tdate = datetime.date.today()
	return tdate.weekday()

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
	title = _get_parent_func_name(title)
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
	title = _get_parent_func_name(title)
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

def jobs_pool(function:str, args:tuple
, pool_size:int=None)->list:
	''' Launches 'pool_size' functions at a time for
		all 'args'.
		Returns list of results.
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
			trace_li = traceback.format_exc().splitlines()
			trace_str = '\n'.join(trace_li[-3:])
			dev_print(f'decor_except exception:\n{trace_str}')
			return e
	return wrapper

TDCBF_OK_BUTTON = 1
TDCBF_YES_BUTTON = 2
TDCBF_NO_BUTTON = 4
TDCBF_CANCEL_BUTTON = 8
TDCBF_RETRY_BUTTON = 16
TDCBF_CLOSE_BUTTON = 32

TD_ICON_BLANK = 100
TD_ICON_WARNING = 101
TD_ICON_QUESTION = 102
TD_ICON_ERROR = 103
TD_ICON_INFORMATION = 104
TD_ICON_BLANK_AGAIN = 105
TD_ICON_SHIELD = 106

TDF_ENABLE_HYPERLINKS = 1
TDF_USE_HICON_MAIN = 2
TDF_USE_HICON_FOOTER = 4
TDF_ALLOW_DIALOG_CANCELLATION = 8
TDF_USE_COMMAND_LINKS = 16
TDF_USE_COMMAND_LINKS_NO_ICON = 32
TDF_EXPAND_FOOTER_AREA = 64
TDF_EXPANDED_BY_DEFAULT = 128
TDF_VERIFICATION_FLAG_CHECKED = 256
TDF_SHOW_PROGRESS_BAR = 512
TDF_SHOW_MARQUEE_PROGRESS_BAR = 1024
TDF_CALLBACK_TIMER = 2048
TDF_POSITION_RELATIVE_TO_WINDOW = 4096
TDF_RTL_LAYOUT = 8192
TDF_NO_DEFAULT_RADIO_BUTTON = 16384
TDF_CAN_BE_MINIMIZED = 32768

_TaskDialogIndirect = ctypes.WinDLL('comctl32.dll').TaskDialogIndirect

_callback_type = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.wintypes.HWND, ctypes.wintypes.UINT
	, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_long))

class _TaskDialogConfig(ctypes.Structure):
	class TASKDIALOG_BUTTON(ctypes.Structure):
		_pack_ = 1
		_fields_ = [
			('nButtonID', ctypes.wintypes.INT)
			, ('pszButtonText', ctypes.wintypes.LPCWSTR)
		]

	class DUMMYUNIONNAME(ctypes.Union):
		_pack_ = 1
		_fields_ = [
			('hMainIcon', ctypes.wintypes.HICON)
			, ('pszMainIcon', ctypes.wintypes.LPCWSTR)
		]

	class DUMMYUNIONNAME2(ctypes.Union):
		_pack_ = 1
		_fields_ = [
			('hFooterIcon', ctypes.wintypes.HICON)
			, ('sFooterIcon', ctypes.wintypes.LPCWSTR)
		]

	_pack_ = 1
	_fields_ = [
		('cbSize', ctypes.wintypes.UINT)
		, ('hwndParent', ctypes.wintypes.HWND)
		, ('hInstance', ctypes.wintypes.HINSTANCE)
		, ('dwFlags', ctypes.wintypes.UINT)
		, ('dwCommonButtons', ctypes.wintypes.UINT)
		, ('pszWindowTitle', ctypes.wintypes.LPCWSTR)
		, ('DUMMYUNIONNAME', DUMMYUNIONNAME)
		, ('pszMainInstruction', ctypes.wintypes.LPCWSTR)
		, ('pszContent', ctypes.wintypes.LPCWSTR)
		, ('cButtons', ctypes.wintypes.UINT)
		, ('pButtons', ctypes.POINTER(TASKDIALOG_BUTTON))
		, ('nDefaultButton', ctypes.wintypes.INT)
		, ('cRadioButtons', ctypes.wintypes.UINT)
		, ('pRadioButtons', ctypes.POINTER(TASKDIALOG_BUTTON))
		, ('nDefaultRadioButton', ctypes.wintypes.INT)
		, ('pszVerificationText', ctypes.wintypes.LPCWSTR)
		, ('pszExpandedInformation', ctypes.wintypes.LPCWSTR)
		, ('pszExpandedControlText', ctypes.wintypes.LPCWSTR)
		, ('pszCollapsedControlText', ctypes.wintypes.LPCWSTR)
		, ('DUMMYUNIONNAME2', DUMMYUNIONNAME2)
		, ('pszFooter', ctypes.wintypes.LPCWSTR)
		, ('pfCallBack', ctypes.POINTER(_callback_type))
		, ('lpCallbackData', ctypes.wintypes.LPLONG)
		, ('cxWidth', ctypes.wintypes.UINT)
	]

	def __init__(self):
		self.cbSize = ctypes.sizeof(self)

def dialog(msg:str=None, buttons:list=None
, title:str=None, content:str=None, flags:int=None
, common_buttons:int=None, default_button:int=0
, timeout:int=None, icon=None)->int:
	''' Shows dialog with multiple optional buttons.
		Returns ID of selected button starting with 1000.
	'''
	TDN_TIMER = 4
	S_OK = 0
	TDM_CLICK_BUTTON = win32con.WM_USER + 102
	TDM_SET_ELEMENT_TEXT = win32con.WM_USER + 108
	TDE_FOOTER = 2
	on_top_flag = False
	@_callback_type
	def callback_timer(hwnd, uNotification:int
	, wParam:int, lParam:int, lpRefData:int):
		nonlocal on_top_flag
		if uNotification == TDN_TIMER:
			mm_ss = time.strftime(
				'%M:%S'
				, time.gmtime(
					1 + (lpRefData.contents.value - wParam) / 1000
				)
			)
			win32gui.SendMessage(
				hwnd, TDM_SET_ELEMENT_TEXT
				, TDE_FOOTER, mm_ss
			)
			if wParam  >= lpRefData.contents.value:
				wParam = 0
				win32gui.SendMessage(
					hwnd, TDM_CLICK_BUTTON, None, None)
		else:
			if not on_top_flag:
				win32gui.SetWindowPos(
					hwnd
					, win32con.HWND_TOPMOST
					, 0, 0, 0, 0
					, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE
				)
				on_top_flag = True
		
		return S_OK
	if isinstance(msg, list):
		buttons = msg
		msg = ''
	title = _get_parent_func_name(title)
	result = ctypes.c_int()
	tdc = _TaskDialogConfig()
	if common_buttons:
		tdc.dwCommonButtons = common_buttons
	if flags:
		tdc.dwFlags = flags
	else:
		tdc.dwFlags = TDCBF_CANCEL_BUTTON
		if timeout: tdc.dwFlags |= TDF_CALLBACK_TIMER
	if isinstance(buttons, (list, tuple)):
		tdc.dwFlags |= TDF_USE_COMMAND_LINKS
		p_buttons = (tdc.TASKDIALOG_BUTTON * len(buttons))
		buttons_li = []
		for num, button_text in enumerate(buttons):
			button = _TaskDialogConfig.TASKDIALOG_BUTTON()
			button.nButtonID = ctypes.c_int(1000 + num)
			button.pszButtonText = ctypes.c_wchar_p(button_text)
			buttons_li.append(button)
		p_buttons = p_buttons(*buttons_li)
		tdc.pButtons = ctypes.cast(
			p_buttons
			, ctypes.POINTER(
				_TaskDialogConfig.TASKDIALOG_BUTTON)
		)
		tdc.cButtons = ctypes.c_uint(len(buttons))
		tdc.nDefaultButton = 1000 + default_button
	tdc.pszMainIcon = TD_ICON_INFORMATION
	tdc.pfCallBack = ctypes.cast(
		callback_timer, ctypes.POINTER(_callback_type))
	if timeout:
		tdc.dwFlags |= TDF_EXPAND_FOOTER_AREA
		tdc.pszFooter = ctypes.c_wchar_p(f'{timeout}')
		value, coef = value_unit(timeout, _TIME_UNITS, 1000)
		timeout = int(value * coef)
		tdc.lpCallbackData = ctypes.pointer(ctypes.c_long(timeout))
	tdc.pszMainInstruction = ctypes.c_wchar_p(msg)
	tdc.pszWindowTitle = ctypes.c_wchar_p(title)
	tdc.pszContent = ctypes.c_wchar_p(content)
	_TaskDialogIndirect(ctypes.byref(tdc)
		, ctypes.byref(result), None, None)
	return result.value

# - - - TaskDialog - - -