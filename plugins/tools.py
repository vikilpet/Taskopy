import sys
import os
import time
import datetime
import statistics
import pytz
import threading
import psutil
import sqlite3
import subprocess
import pywintypes
from multiprocessing.dummy import Pool as ThreadPool
from operator import itemgetter
import re
import winsound
import locale
import contextlib
import glob
import getpass
import traceback
import inspect
import ctypes
import pyperclip
import random
import functools
import importlib
import string
import win32gui
import win32con
import win32com.client
from typing import List, Tuple, Callable \
	, Union, Iterable, Iterator
from itertools import zip_longest
import pythoncom
import wx
from collections import defaultdict
import lxml
import textwrap
from xml.etree import ElementTree as _ElementTree
try:
	import constants as tcon
except ModuleNotFoundError:
	import plugins.constants as tcon

APP_NAME = 'Taskopy'
APP_VERSION = 'v2023-01-28'
APP_FULLNAME = APP_NAME + ' ' + APP_VERSION
_app_log = []

if not __builtins__.get('gdic', None):
	gdic = {}
	__builtins__['gdic'] = gdic
	_app:wx.App = None
	__builtins__['_app'] = _app

_DEFAULT_INI = r'''[General]
language=en
editor=notepad.exe
hide_console=False

[HTTP]
server_ip=127.0.0.1
server_port=8275
white_list=127.0.0.1
'''
if getattr(sys, 'frozen', False):
	_APP_PATH = os.path.dirname(sys.executable)
else:
	_APP_PATH = os.getcwd()
_TIME_UNITS = {
	'millisecond': 1, 'milliseconds': 1, 'msec': 1, 'ms': 1
	, 'second': 1000, 'seconds': 1000, 'sec': 1000, 's': 1000
	, 'minute': 60_000, 'minutes': 60_000, 'min': 60_000, 'm': 60_000
	, 'hour': 3_600_000, 'hours': 3_600_000, 'h': 3_600_000
	, 'day': 86_400_000, 'days': 86_400_000, 'd': 86_400_000
	, 'week': 604_800_000, 'weeks': 604_800_000, 'w': 604_800_000
	, 'month': 2_635_200_000, 'months': 2_635_200_000, 'mn': 2_635_200_000
	, 'year': 31_536_000_000, 'years': 2_31_536_000_000, 'y': 31_536_000_000
}
_LOCALE_LOCK = threading.Lock()
_LOG_TIME_FORMAT = '%Y.%m.%d %H:%M:%S'

class DictToObj:
	''' Converts dictionary to object.
		Convert back: use vars() built-in function.
	'''
	def __init__(self, di:dict):
		self.__dict__.update(di)

	def __getattr__(self, name):
		return 'DictToObj - unknown key'

def value_to_unit(value, unit:str='sec', unit_dict:dict=None
, def_src_unit:str='sec')->float:
	'''
	Converts a string with a number and unit of measure
	to the desired unit of measure.
	Usage:

		tass( value_to_unit('1 min', 'sec'), 60.0)
		tass( value_to_unit('2m', 'sec'), 120.0)
		tass( value_to_unit(3, 'sec'), 3.0)

	'''
	if not unit_dict: unit_dict = _TIME_UNITS
	unit = unit.lower()
	dst_coef = unit_dict[unit]
	if isinstance(value, (int, float)):
		value = [value, def_src_unit]
	if isinstance(value, (list, tuple)):
		v, u = value
		src_coef = unit_dict[u.lower()]
		return (int(v) * src_coef) / dst_coef
	elif value.isdigit():
		return int(value)
	elif ' ' in value:
		v, u = value.split()
		src_coef = unit_dict[u.lower()]
		return (int(v) * src_coef) / dst_coef
	elif any(i.isdigit() for i in value):
		v = ''.join(filter(str.isdigit, value))
		u = ''.join(filter(lambda v: not v.isdigit(), value))
		src_coef = unit_dict[u.lower()]
		return (int(v) * src_coef) / dst_coef
	else:
		raise('Wrong value')

def _get_parents()->list:
	' Returns a list with parent functions '
	SKIP_LIST = ('thread_start', '<module>', '__init__')
	parents = []
	for lvl in range(1, 10):
		try:
			parent = sys._getframe(lvl).f_code.co_name
			if parent in SKIP_LIST: continue
			parents.append(parent)
		except ValueError:
			break
	return parents

def _get_parent_func_name(parent=None, repl_undrsc:str=None)->str:
	''' Get name of parent function if any '''
	EXCLUDE = ('wrapper', 'run_task', 'run', 'dev_print', 'tprint'
		, 'main', 'run_task_inner', 'popup_menu_hk'
		, 'MainLoop', 'catcher', 'run_code', 'mapstar'
		, 'run_ast_nodes')
	if parent: return str(parent)
	for i in range(2, 10):
		try:
			parent = sys._getframe(i).f_code.co_name
		except ValueError:
			parent = ''
			break
		if parent == 'con_log': return ''
		if (
			not parent in EXCLUDE
			and not parent.startswith('_')
			and not parent.startswith('<')
		):
			break
	else:
		parent = ''
	if repl_undrsc != None:
		parent = parent.replace('_', repl_undrsc)
	return parent

def task(**kwargs):
	def with_attrs(func):
		for key, value in kwargs.items():
			setattr(func, key, value)
		setattr(func, 'is_task', True)
		return func
	return with_attrs

def sound_play(fullpath, wait=False):
	'''
	Play .wav sound. If fullpath is a folder then pick random file.
	If fullpath is a list then pick random file from this list.
	'''
	if isinstance(fullpath, (list, tuple)):
		fi = random.choice(fullpath)
	elif os.path.isdir(fullpath):
		fi = random.choice(glob.glob(fullpath + '\\*'))
	else:
		fi = fullpath
	if wait:
		winsound.PlaySound(fi, winsound.SND_FILENAME)
	else:
		winsound.PlaySound(fi, winsound.SND_FILENAME + winsound.SND_ASYNC)

def dev_print(*msg, **kwargs):
	if is_dev() or tdebug():
		tprint(*msg, **kwargs)

def is_dev()->bool:
	return ('--developer' in sys.argv) or hasattr(sys, 'ps1')

def con_log(*msgs, **kwargs):
	''' Log to console and logfile
	'''
	global _app_log
	log_str = ''
	ltime = datetime.datetime.now()
	for msg in msgs:
		tprint(msg, **kwargs)
		_app_log.append((ltime, msg))
		log_str += (
			ltime.strftime(_LOG_TIME_FORMAT)
			+ ' ' + str(msg) + '\n'
		)
	try:
		if not (sett := __builtins__.get('sett', None)): return
		with open(
			f'log\\{ltime.strftime(sett.log_file_name)}.log'
			, 'ta+', encoding='utf-8'
		) as f:
			f.write(log_str)
	except FileNotFoundError:
		os.makedirs('log')
		with open(
			f'log\\{ltime.strftime(sett.log_file_name)}.log'
			, 'ta+', encoding='utf-8'
		) as f:
			f.write(log_str)

def time_now_str(template:str=tcon.DATE_STR_FILE
, use_locale:str='C', timezone=None, **delta)->str:
	'''
	Returns a string with current time.
	'''
	if not delta:
		return time_str(
			template=template
			, use_locale=use_locale
			, timezone=timezone
		)
	return time_str(
		time_val=time_now(**delta)
		, template=template
		, use_locale=use_locale
		, timezone=timezone
	)

def time_str(template:str=tcon.DATE_STR_FILE
, time_val:datetime.datetime=None
, use_locale:str='C', timezone=None)->str:
	'''
	Returns time in the form of a string in specified locale.
	
	Use datetime in `time_val`. How to get yesterday's date:

		time_val = datetime.date.today() - datetime.timedelta(days=1)

	'''
	if timezone == 'utc':
		timezone = pytz.utc
	elif isinstance(timezone, str):
		timezone = pytz.timezone(timezone)
	if isinstance(time_val, float):
		time_val = datetime.datetime.fromtimestamp(time_val, tz=timezone)
	elif not time_val:
		time_val = datetime.datetime.now(tz=timezone)
	with locale_set(use_locale):
		return time_val.strftime(template)

def time_now(**delta)->datetime.datetime:
	'''
	Returns datetime object.
	Use `datetime.timedelta` keywords to get different time.
	Yesterday:

		time_now(days=-1)

	'''
	if not delta: return datetime.datetime.now()
	return ( datetime.datetime.now() + datetime.timedelta(**delta) )

def time_from_str(date_string:str, template:str=tcon.DATE_STR_FILE
, use_locale:str='C')->datetime.datetime:
	'''
	Returns datetime object from string and
	specified locale.
	'''
	with locale_set(use_locale):
		return datetime.datetime.strptime(date_string, template)

def time_hour()->int:
	'''Returns current hour'''
	return datetime.datetime.now().hour

def time_minute()->int:
	'''Returns current minute'''
	return datetime.datetime.now().minute

def time_second()->int:
	'''Returns current second'''
	return datetime.datetime.now().second

def time_diff(start:datetime.datetime, end:datetime.datetime=None
, unit:str='sec')->int:
	'''
	Returns difference in units.
	start and end should be in datetime format.
	'''
	if not end: end = datetime.datetime.now()
	seconds = (end - start).total_seconds()
	coef = _TIME_UNITS.get(unit, 1000) / 1000
	return int(seconds // coef)

def time_diff_str(start:datetime.datetime
, end:datetime.datetime=None, str_format:str=''
, no_ms:bool=False)->str:
	'''
	Returns time difference as a string like that:
	'5 days, 3:01:35.837127'
	
	*start* and *end* should be in _datetime_ format.
	
	*str_format* - standard time formating like '%y.%m.%d %H:%M:%S'
	(see tcon.DATE_FORMAT)

	*no_ms* - do not show microseconds.

	'''
	if isinstance(start, float):
		start = datetime.datetime.fromtimestamp(start)
	if not end: end = datetime.datetime.now()
	if not str_format:
		if no_ms:
			return str(end - start).split('.')[0]
		else:
			return str(end - start)
	delta_as_time = time.gmtime( (end - start).total_seconds() )
	return time.strftime(str_format, delta_as_time)

def _date_part(date_val:datetime.datetime=None, part:str=''):
	if not date_val: date_val = datetime.datetime.now()
	return getattr(date_val, part)

def date_year(date_val:datetime.datetime=None)->int:
	'''Returns year'''
	return _date_part(part='year')

def date_month(date_val:datetime.datetime=None)->int:
	'''Returns month number'''
	return _date_part(part='month')

def date_day(date_val:datetime.datetime=None, delta:dict=None)->int:
	''' Returns current day of months (1-31) '''
	if not delta: return _date_part(part='day')
	if not date_val: date_val = datetime.datetime.now()
	return ( date_val + datetime.timedelta(**delta) ).day

def date_weekday(date_val:datetime.datetime=None
, template:str='%A')->str:
	'''
	Returns weekday as a string.
	'''
	if not date_val: date_val = datetime.date.today()
	return date_val.strftime(template)

def date_weekday_num(date_val:datetime.datetime=None)->int:
	'''
	Weekday number (monday is 1).  
	*tdate* - None (today) or datetime.date(2019, 6, 12)

		tass( date_weekday_num(datetime.date(2022, 9, 12) ), 1)

	'''
	if not date_val: date_val = datetime.date.today()
	return date_val.weekday() + 1

def date_fill(date_dic:dict, cur_date=None)->datetime.datetime:
	r'''
	Fills `None` values in dictionary with current
	datetime value.
	Example:

		dt_dic = {'year': None, 'month': 11
		, 'day': 26, 'hour': 23, 'minute': 24}
		date_fill(dt_dic)
		tass( benchmark(date_fill, 10, a=(dt_dic,)), 5000, '<' )

	'''
	new_date_dic = {'year': 0, 'month': 0
	, 'day': 0, 'hour': 0, 'minute': 0}
	if cur_date == None: cur_date = datetime.datetime.now()
	for part in new_date_dic:
		if date_dic[part] == None:
			new_date_dic[part] = getattr(cur_date, part)
		else:
			new_date_dic[part] = date_dic[part]
	return datetime.datetime(**new_date_dic)

def date_fill_str(date_str:str)->str:
	r'''
	Replace asterisk to current datetime value:  
	date_fill_str('*.*.01 12:30') -> '2020.10.01 12:30'

		tass(
			benchmark(date_fill_str, 100, a=('*.*.01 12:30',))
			, 7000
			, '<'
		)

	'''
	if not '*' in date_str: return date_str
	date_str = date_str.replace('.', ' ').replace(':', ' ')
	new_date_lst = list( datetime.datetime.now().timetuple() )
	for pos, value  in enumerate( date_str.split() ):
		if value != '*': new_date_lst[pos] = value
	return '{:0>4}.{:0>2}.{:0>2} {:0>2}:{:0>2}' \
		.format(*new_date_lst)

def time_sleep(interval, unit:str=None):
	''' Pauses for specified amount of time.
		interval - number of seconds or str with unit like '5 min'
		or tuple with (start, stop) for random interval (you should
		provide unit in this case). Example:

			time_sleep( (2,10), 'sec' )

	'''
	if isinstance(interval, (list, tuple)):
		interval = str( random_num(*interval) ) + ' ' + unit
	elif unit:
		interval = str(interval) + ' ' + unit
	time.sleep( value_to_unit(interval, 'sec') )
pause = time_sleep
wait = time_sleep

def clip_set(txt:str):
	pyperclip.copy(str(txt))

def clip_get()->str:
	return pyperclip.paste()

def re_find(source:str, re_pattern:str, sort:bool=False
, unique:bool=False, re_flags:int=re.IGNORECASE)->List[str]:
	r'''
	Returns list with matches.  
	re_flags:  
	*re.IGNORECASE* - ignore case.  
	*re.MULTILINE* - make begin/end {^, $} consider each line.  
	*re.DOTALL* - make . match newline too.  
	*re.UNICODE* - make {\w, \W, \b, \B} follow Unicode rules.  
	*re.LOCALE* - make {\w, \W, \b, \B} follow locale.  
	*re.VERBOSE* - allow comment in regex.  

	Non-capturing group: (?:aaa)  
	Positive lookbehind: (?<=abc)  
	'''
	matches = re.findall(re_pattern, source, flags=re_flags)
	if unique: matches = list(set(matches))
	if sort: matches.sort()
	return matches

def re_replace(source:str, re_pattern:str, repl:str=''
, re_flags:int=re.IGNORECASE)->str:
	''' Regexp replace substring'''
	return re.sub(
		pattern=re_pattern
		, repl=repl
		, string=source
		, flags=re_flags
	)

def re_split(source:str, re_pattern:str, maxsplit:int=0
, re_flags:int=re.IGNORECASE)->List[str]:
	'''
	Regexp split.
	
		tass( re_split('abc', 'b'), ['a', 'c'] )
	
	'''
	return re.split(
		pattern=re_pattern
		, maxsplit=maxsplit
		, string=source
		, flags=re_flags
	)

def re_match(source:str, re_pattern:str
, re_flags:int=re.IGNORECASE)->bool:
	r'''
	Regexp match.

		tass( re_match('C - 25.11.19.mp3', r'.+ - \d\d\.\d\d\.\d\d.+'), True )
		tass( re_match('C - 25.11.19.mp3', r' - \d\d\.\d\d\.\d\d.+'), False)

	'''
	return bool(re.match(re_pattern, source, flags=re_flags))

_MessageBox = ctypes.windll.user32.MessageBoxW
_MessageBoxTimeout = ctypes.windll.user32.MessageBoxTimeoutW

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
		for sec in reversed(range(100 * (timeout // 1000) ) ):
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
	if title == None:
		title = func_name_human(_get_parent_func_name())
	else:
		title = str(title)
	if ui: ui += win32con.MB_SYSTEMMODAL
	else:
		ui = win32con.MB_ICONINFORMATION + win32con.MB_SYSTEMMODAL
	if timeout:
		mb_func = _MessageBoxTimeout
		title_tmp = title + '          rand' + str(random.randint(100000, 1000000))
		timeout = int( value_to_unit(timeout, 'ms') )
		mb_args = (None, msg, title_tmp, ui, 0, timeout)
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
			thread_start(
				func=lambda *a, r=result: r.append(mb_func(*a))
				, args=mb_args 
			)
			hwnd = get_hwnd(title_tmp)
			if hwnd:
				if dis_timeout:
					thread_start(dis_buttons, args=(hwnd, dis_timeout))
				thread_start(title_countdown, args=(hwnd, timeout, title))
			while not result: time.sleep(0.01)
			if result:
				return result[0]
			else:
				return 0
		else:
			if dis_timeout:
				result = []
				thread_start(lambda *a, r=result: r.append(mb_func(*a))
				, args=mb_args)
				hwnd = get_hwnd(title_tmp)
				if hwnd:
					win32gui.SetWindowText(hwnd, title)
					thread_start(dis_buttons, args=(hwnd, dis_timeout))
				while not result: time.sleep(0.01)
				return result[0]
			else:
				return mb_func(*mb_args)
	else:
		if timeout:
			if dis_timeout:
				thread_start(mb_func, args=mb_args)
				hwnd = get_hwnd(title_tmp)
				if hwnd:
					win32gui.SetWindowText(hwnd, title)
					thread_start(dis_buttons, args=(hwnd, dis_timeout))
					thread_start(title_countdown, args=(hwnd, timeout, title))
			else:
				thread_start(mb_func, args=mb_args)
				hwnd = get_hwnd(title_tmp)
				if hwnd:
					win32gui.SetWindowText(hwnd, title)
					thread_start(title_countdown, args=(hwnd, timeout, title))
		else:
			if dis_timeout:
				thread_start(mb_func, args=mb_args)
				hwnd = get_hwnd(title_tmp)
				if hwnd:
					win32gui.SetWindowText(hwnd, title)
					thread_start(dis_buttons, args=(hwnd, dis_timeout))
			else:
				thread_start(mb_func, args=mb_args)

def warning(msg:str, title:str=None):
	if sett.kiosk:
		con_log(f'warning: {msg}')
		return
	if title:
		title = f'{APP_NAME}: {title}'
	else:
		title = APP_FULLNAME
	msgbox(msg=msg, title=title
	, ui=win32con.MB_ICONWARNING, wait=False
	, timeout='1 hour')

def inputbox(message:str, title:str=None
, is_pwd:bool=False, default:str=''
, multiline:bool=False, topmost:bool=True)->str:
	''' Request input from user.
		is_pwd - use password dialog (hide input).
		Problem: don't use default or you will get this value
		whatever button user will press.
	'''
	if tdebug():
		if is_pwd:
			return getpass.getpass(f'inputbox ({message}): ')
		else:
			return input(f'inputbox ({message}): ')
	if title == None:
		title = func_name_human(_get_parent_func_name())
	else:
		title = str(title)
	if is_pwd:
		box_func = wx.PasswordEntryDialog
	else:
		box_func = wx.TextEntryDialog
	style=(wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP)
	if multiline: style += wx.TE_MULTILINE
	dlg = box_func(app.frame, message, title, style=style)
	win32gui.SetWindowPos(
		dlg.Handle
		, win32con.HWND_TOPMOST \
			if topmost else win32con.HWND_TOP
		, 0, 0, 0, 0
		, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE
	)
	if default: dlg.SetValue(str(default))
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
, wildcard:str='', on_top:bool=True)->str:
	''' Shows standard file dialog
		and returns fullpath or list of fullpaths
		if multiple == True.
		Will not work in console.
	'''

	def decap(s:str): return s[:1].lower() + s[1:] if s else ''

	if title == None:
		title = func_name_human(_get_parent_func_name())
	else:
		title = str(title)
	if tdebug(): return input(f'File dialog ({title}): ')
	style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
	if multiple: style |= wx.FD_MULTIPLE
	if on_top: style |= wx.STAY_ON_TOP
	dialog = wx.FileDialog(None, title, wildcard=wildcard
		, defaultDir=default_dir, defaultFile=default_file, style=style)
	if dialog.ShowModal() == wx.ID_OK:
		if multiple:
			fullpath = dialog.GetPaths()
			fullpath = [decap(f) for f in fullpath]
		else:
			fullpath = decap(dialog.GetPath())
	else:
		fullpath = None
	dialog.Destroy()
	return fullpath

def dir_dialog(title:str=None, default_dir:str='', on_top:bool=True
, must_exist:bool=True)->str:
	''' Shows standard directory dialog
		and returns fullpath.
		Will not work in console.
	'''

	def decap(s:str): return s[:1].lower() + s[1:] if s else ''

	if title == None:
		title = func_name_human(_get_parent_func_name())
	else:
		title = str(title)
	if tdebug(): return input(f'Dir dialog ({title}): ')
	style = wx.DD_DEFAULT_STYLE
	if must_exist: style |= wx.DD_DIR_MUST_EXIST
	if on_top: style |= wx.STAY_ON_TOP
	dialog = wx.DirDialog(None, message=title, defaultPath=default_dir
		, style=style)
	if dialog.ShowModal() == wx.ID_OK:
		fullpath = decap(dialog.GetPath())
	else:
		fullpath = None
	dialog.Destroy()
	return fullpath
random_num = random.randint

def random_str(string_len:int=10, string_source:str=None)->str:
	''' Generate a random string of fixed length
	'''
	if not string_source:
		string_source = string.ascii_letters + string.digits
	return ''.join(
		random.choice(string_source) for i in range(string_len)
	)

def app_icon_text_set(text:str=APP_FULLNAME):
	''' Set hint text for taskbar icon.
	'''
	global app
	app.taskbaricon.set_icon(text=text)

def create_default_ini_file():
	''' Creates default settings.ini file.
	'''
	with open('settings.ini', 'xt', encoding='utf-8-sig') as ini:
		ini.write(_DEFAULT_INI)

def job_pool(jobs:list, pool_size:int=None)->list:
	'''	Launches 'pool_size' jobs at a time.
		Returns the same jobs list.
		See Job class for job properties.
		If 'pool_size' not specified, pool_size = number of CPU.
		Example:

			jobs = []
			for w in "Let's test job pool".split():
				jobs.append(
					Job(
						dialog
						, w
					)
				)
			for job in job_pool(jobs, pool_size=2):
				print(job.error, job.result, job.time)
	'''
	pool = ThreadPool(pool_size)
	pool.map(lambda f: f(), (j.run for j in jobs))
	pool.close()
	pool.join()
	return jobs

class Job:
	'''
	To use with job_batch and job_pool.
	Example with type annotation:
	
		jobs = []
		for i in range(4): jobs.append( Job(
			dialog
			, msg=f'Job {i}'
			, buttons=('Yes', 'No')
		) )
		jobs.append( Job(lambda: 0/0) )
		job: Job
		for job in job_pool(jobs):
			if job.error:
				print('error:', job.result)
			else:
				print('result:', job.result)

	'''
	def __init__(
		self
		, func
		, *args
		, job_name:str=''
		, **kwargs
	):
		self.func = func
		self.args = args
		self.kwargs = kwargs
		self.finished = False
		self.result = None
		self.time = 0
		self.error = False
		self.job_name = job_name
	
	def run(self):
		time_start = time.time()
		try:
			self.result = self.func(*self.args, **self.kwargs)
			if isinstance(self.result, Exception):
				self.error = True
				self.result = f'Exception: {repr(self.result)}' \
				+ f'\nat line {self.result.__traceback__.tb_lineno}'
		except Exception as e:
			self.result = f'Exception: {repr(e)}' \
				+ f'\nat line {e.__traceback__.tb_lineno}'
			self.error = True
		self.finished = True
		self.time = datetime.timedelta(
			seconds=(time.time() - time_start)
		)

def job_batch(jobs:list, timeout:int
, sleep_timeout:float=0.001)->list:
	'''
	Starts functions (they do not necessarily
	have to be the same) in parallel and waits for
	them to be executed or timeout.
	Use this when you don't want to wait because
	of one hung function.

	jobs - list of Job objects (see class Job for details).
	
	timeout - timeout in seconds.

	Returns same list of job objects.
	Usage example:
		
		jobs = []
		jobs.append(
			Job(dialog, 'Test job 1')
		)
		jobs.append(
			Job(dialog, ['Button 1', 'Button 2'])
		)
		for job in job_batch(jobs, timeout=5):
			print(job.error, job.result, job.time)
	
	'''
	for job in jobs:
		thread_start(job.run)
	for _ in range(int(timeout / sleep_timeout)):
		if all((j.finished for j in jobs)):
			return jobs
		time.sleep(sleep_timeout)
	else:
		for job in jobs:
			if not job.finished:
				job.error = True
				job.result = 'timeout'
				job.time = 'timeout'
		return jobs

def tprint(*msgs, **kwargs):
	''' Print with task name and time '''
	parent = _get_parent_func_name()
	msgs = list(msgs)
	if parent: msgs.insert(0, parent + ':')
	print(time.strftime('%y.%m.%d %H:%M:%S'), *msgs, **kwargs)

def tdebug(*msgs, **kwargs)->bool:
	''' Is the code running from the console? '''
	if not hasattr(sys, 'ps1'): return False
	if msgs:
		if kwargs.get('par', True):
			msg = _get_parent_func_name() + ': '
		else:
			msg = ''
		if isinstance(msgs, dict):
			msg += '\n'.join(f'{k}:{v}' for k, v in msgs.items())
		else:
			msg += ' '.join(map(str, msgs))
		print(msg)
	return True

def balloon(msg:str, title:str=APP_NAME, timeout:int=None, icon:str=None):
	''' Show balloon. title - 63 symbols max, msg - 255.
		icon - 'info', 'warning' or 'error'.
	'''
	kwargs = {'title': title, 'text': msg}
	if tdebug():
		tprint('balloon:', msg)
		return
	if timeout: kwargs['msec'] = timeout * 1000
	if icon:
		kwargs['flags'] = {
			'info': wx.ICON_INFORMATION
			, 'error': wx.ICON_ERROR
			, 'warning': wx.ICON_WARNING
		}.get(icon.lower(), wx.ICON_INFORMATION)
	app.taskbaricon.ShowBalloon(**kwargs)

def app_log_get()->str:
	'''
	Returns current log as a string.
	Log can't be empty.
	'''
	log = [t.strftime(_LOG_TIME_FORMAT) + ' ' + m for t, m in _app_log]
	return '\n'.join(log)

def decor_except(func):
	''' Add 'try... except' for function
		and return Exception object on fail.

		Downside - iPython autoreload does not
		work for decorated 'func'.
	'''
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except Exception as e:
			trace_li = traceback.format_exc().splitlines()
			trace_str = '\n'.join(trace_li[-3:])
			tdebug(f'decor_except exception:\n{trace_str}')
			return e
	return wrapper

def decor_except_status(func):
	''' Adds 'try... except' for function and returns
		(True, result) or (False, Exception).

		Downside - iPython autoreload does not
		work for decorated 'func'.
	'''
	@functools.wraps(func)
	def wrapper(*args, **kwargs) -> tuple:
		try:
			if kwargs.get('safe', False):
				return (True, func(*args, **kwargs))
			else:
				return func(*args, **kwargs)
		except Exception as e:
			trace_li = traceback.format_exc().splitlines()
			trace_str = '\n'.join(trace_li[-3:])
			tdebug(f'decor_except exception:\n{trace_str}')
			if kwargs.get('safe', False):
				e.args = (f'Safe {func.__name__}: {", ".join(e.args)}', )
				return (False, e)
			else:
				return e
	if getattr(func, 'homemade', False):
		return func
	else:
		wrapper.homemade = True
		if 'safe' in inspect.signature(func).parameters.keys():
			return wrapper
		else:
			return func
decor_except_status.homemade = True

def safe(func:Callable)->Callable:
	'''
	Evaluate function inside 'try... except'
	and return (True, <function result>)
	or (False, Exception)
	'''
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		try:
			res = func(*args, **kwargs)
			if isinstance(res, Exception):
				return False, res
			else:
				return True, res
		except Exception as e:
			trace_li = traceback.format_exc().splitlines()
			trace_str = '\n'.join(trace_li[-3:])
			tdebug(f'safe: \n{trace_str}')
			return False, e
	return wrapper
_TaskDialogIndirect = ctypes.WinDLL('comctl32.dll').TaskDialogIndirect

_callback_type = ctypes.WINFUNCTYPE(
	ctypes.c_int, ctypes.wintypes.HWND, ctypes.wintypes.UINT
	, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_long)
)

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

def dialog(
	msg:Iterable=''
	, buttons:Union[Iterable, None]=None
	, title:str=''
	, content:str=''
	, flags:int=0
	, common_buttons:Union[int, None]=None
	, default_button:int=0
	, timeout:Union[str, int]=0
	, return_button:bool=False
	, wait:bool=True
)->Union[int, str]:
	'''
	Shows dialog with multiple optional buttons.
	Returns ID of selected button starting with 1000
	or 0 if timeout is over.
	return_button - returns (status, selected button value).
		Status == True if some of button was selected and
		False if no button was selected (timeout or escape).

	wait - non-blocking mode. It returns c_long object
	so it is possible to get user responce later with
	'.value' property (=2 before user makes any choice)
	
	Note: do not start button text with new line (\\n) or dialog
	will fail silently.

		assert dialog(('y', 'n'), return_button=True) == (True, 'y')
		assert dialog({'y': 1, 'n': 2}) == 1

	'''
	TDN_TIMER = 4
	S_OK = 0
	TDM_CLICK_BUTTON = win32con.WM_USER + 102
	TDM_SET_ELEMENT_TEXT = win32con.WM_USER + 108
	TDE_FOOTER = 2
	on_top_flag = False
	TDCBF_CANCEL_BUTTON = 8
	TDF_CALLBACK_TIMER = 2048
	TDF_USE_COMMAND_LINKS = 16
	TDF_EXPAND_FOOTER_AREA = 64
	TD_ICON_INFORMATION = 104
	
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
				try:
					win32gui.SetWindowPos(
						hwnd
						, win32con.HWND_TOPMOST
						, 0, 0, 0, 0
						, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE
					)
					on_top_flag = True
				except Exception as e:
					raise Exception('dialog: wrong parameters')
		return S_OK
	if content: content = str(content)
	if title == '':
		title = func_name_human(_get_parent_func_name())
	else:
		title = str(title)
	if is_iter(msg):
		buttons = msg
		msg = ''
	else:
		if msg: msg = str(msg)
	orig_buttons = ()
	if buttons:
		orig_buttons = buttons
		if isinstance(buttons, dict):
			buttons = tuple(map(str, buttons.keys()))
		else:
			buttons = tuple(map(str, buttons))
		assert not any(b.startswith('\n') for b in buttons), 'wrong buttons'
		assert not any(b == '' for b in buttons), 'wrong buttons'
	result = ctypes.c_int()
	tdc = _TaskDialogConfig()
	if common_buttons:
		tdc.dwCommonButtons = common_buttons
	if flags:
		tdc.dwFlags = flags
	else:
		tdc.dwFlags = TDCBF_CANCEL_BUTTON
		if timeout: tdc.dwFlags |= TDF_CALLBACK_TIMER
	if isinstance(buttons, (list, tuple, set)):
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
		if default_button >= 1000: default_button -= 1000
		tdc.nDefaultButton = 1000 + default_button
	tdc.pszMainIcon = TD_ICON_INFORMATION
	tdc.pfCallBack = ctypes.cast(
		callback_timer, ctypes.POINTER(_callback_type))
	if timeout:
		tdc.dwFlags |= TDF_EXPAND_FOOTER_AREA
		tdc.pszFooter = ctypes.c_wchar_p(f'{timeout}')
		timeout = int( value_to_unit(timeout, 'ms') )
		tdc.lpCallbackData = ctypes.pointer(ctypes.c_long(timeout))
	tdc.pszMainInstruction = ctypes.c_wchar_p(msg)
	tdc.pszWindowTitle = ctypes.c_wchar_p(title)
	tdc.pszContent = ctypes.c_wchar_p(content)
	if wait:
		_TaskDialogIndirect(ctypes.byref(tdc)
			, ctypes.byref(result), None, None)
	else:
		thread_start(lambda: _TaskDialogIndirect(ctypes.byref(tdc) \
			, ctypes.byref(result), None, None))
		return
	if buttons and return_button:
		if result.value >= 1000:
			return True, orig_buttons[result.value - 1000]
		else: 
			return False, result.value
	else:
		if not isinstance(orig_buttons, dict):
			return result.value
		if result.value >= 1000:
			return tuple(orig_buttons.values())[result.value - 1000]
		else:
			return result.value

def hint(text:str, position:tuple=None)->int:
	'''	Shows hint.
		Returns PID of new process.
	'''
	hint_file = os.path.join(os.getcwd(), 'resources', 'hint.py')
	args = [
		'python'
		, hint_file
		, '--text', str(text)
	]
	if position: args += '--position', '{}_{}'.format(*position)
	if getattr(sys, 'frozen', False):
		mdl = importlib.import_module('resources.hint')
		thread_start(
			mdl.main
			, kwargs={'text': text, 'position': position}
		)
	else:
		return subprocess.Popen(args=args
		, creationflags=win32con.DETACHED_PROCESS).pid

@contextlib.contextmanager
def locale_set(name:str='C'):
	with _LOCALE_LOCK:
		saved = locale.setlocale(locale.LC_ALL)
		try:
			yield locale.setlocale(locale.LC_ALL, name)
		finally:
			locale.setlocale(locale.LC_ALL, saved)

def table_print(
	table
	, use_headers=False
	, row_sep:str=''
	, headers_sep:str='-'
	, col_pad:str='  '
	, row_sep_step:int=0
	, sorting:tuple=()
	, sorting_func=None
	, sorting_rev:bool=False
	, repeat_headers:int=None
	, empty_str:str='-'
	, consider_empty:tuple=(None, '')
	, max_table_width:Union[int, tuple]=()
	, trim_func=None
):
	'''
	Print list of lists/tuples as a table.

	*use_headers* - if it's True - takes first row as
	a headers. If list, then use this list as
	a headers.  
	*sorting* - list of column numbers to sort by.  
	Example:
	sorting=[0, 1] - sort table by first
	and second column  
	*sorting_func* - sort with this function.  
	*sorting_rev* - sort in reverse order.  
	*row_sep* - string to repeat as a row separator.  
	*headers_sep* - same for header(s).  
	*max_table_width* - maximum width and number of
	the column to trim or just the maximum width. In that
	case column number will be set to the number of
	last column.  
	*trim_func* - function to trim a long string. If not
	set then internal *trim_str* will be used. The function
	receives a string and its maximum length as input.
	
	Example:

		table = [
			('Header-1', 'Header-2', 'Header-3')
			, *(
				(random_str(3), random_str(100), random_str(5))
				for _ in range(3)
			)
		]
		table_print(table, max_table_width=(100, 1))

	'''

	DEF_SEP = '-'

	def trim_str(string:str, max_len:int):
		' Trim the string if its length exceeds *max_len* '
		if len(string) <= max_len: return string
		return '...' + string[-max_len + 3 : ]

	def print_sep(sep=row_sep):
		nonlocal table_width
		if not sep: return
		print( sep * (table_width // len(sep) ) )
	
	def print_headers(both=False):
		nonlocal headers, template
		if not headers: return
		if both: print_sep(sep=headers_sep)
		print(template.format(*headers))
		print_sep(sep=headers_sep)

	headers = []
	if not table: return
	if use_headers and not headers_sep: headers_sep = DEF_SEP
	if row_sep_step and not row_sep: row_sep = DEF_SEP
	if row_sep and not headers_sep: headers_sep = row_sep
	if isinstance(table, dict):
		rows = [list( di.values() ) for di in table.values()]
		if use_headers == True: headers = list(
			list( table.values() )[0].keys() )
	elif isinstance(table[0], dict):
		rows = [list( di.values() ) for di in table]
		if use_headers == True: headers = list( table[0].keys() )
	elif isinstance(table[0], list):
		rows = [l[:] for l in table]
	elif isinstance(table[0], tuple):
		rows = [list(t) for t in table]
	if is_iter(use_headers):
		headers = tuple(use_headers)
	elif use_headers == True:
		try:
			headers = rows.pop(0)
		except UnboundLocalError:
			raise Exception(
				'table_print: the first row must be list of headers')
	if sorting: sort_key = itemgetter(*sorting)
	if sorting_func:
		if isinstance(sorting_func, (tuple, list)):
			sfunc, item = sorting_func
		else:
			sfunc = sorting_func
			item = 0
		sort_key = lambda l, f=sfunc, i=item: f(l[i])
	if sorting or sorting_func:
		if use_headers:
			rows = [ headers, *sorted(rows, key=sort_key
				, reverse=sorting_rev) ]
		else:
			rows.sort(key=sort_key, reverse=sorting_rev)
	else:
		if headers: rows.insert(0, headers)
	new_rows = []
	for row in rows:
		new_row = []
		for cell in row:
			if cell in consider_empty:
				cell = empty_str
			elif isinstance(cell, (int, float)):
				cell = '{:,}'.format(cell).replace(',', ' ')
			else:
				cell = ' '.join( str(cell).splitlines() )
			new_row.append(cell)
		new_rows.append(new_row)
	rows = new_rows
	col_sizes = tuple( max( map(len, col) ) for col in zip(*rows) )
	table_width = sum(col_sizes) + len(col_pad) * (len(col_sizes) - 1)
	trim_len, trim_col = 0, 0
	if max_table_width and isinstance(max_table_width, int):
		max_table_width = (max_table_width, len(rows[0]) - 1)
	if max_table_width and (table_width > max_table_width[0]):
		trim_col = max_table_width[1]
		trim_len = (
			col_sizes[trim_col] - (table_width - max_table_width[0])
		)
		new_rows = []
		if not trim_func: trim_func = trim_str
		for row in rows:
			new_rows.append((
				*row[:trim_col]
				, trim_func(row[trim_col], trim_len)
				, *row[trim_col + 1:]
			))
		rows = new_rows
		col_sizes = [ max( map(len, col) ) for col in zip(*rows) ]
		table_width = max_table_width[0]
	template = col_pad.join(
		[ '{{:<{}}}'.format(s) for s in col_sizes ]
	)
	if headers: rows.pop(0)
	print()
	if headers: print_headers(False)
	for row_num, row in enumerate(rows):
		if row_sep_step:
			pr = (row_num > 0)  and (row_num % row_sep_step == 0)
			if pr:
				print_sep()
			if repeat_headers:
				if headers and row_num > 0 \
				and (row_num % repeat_headers == 0):
					print_headers(not pr)
		else:
			if repeat_headers:
				if row_num > 0 and (row_num % repeat_headers == 0):
					print_headers(True)
		print(template.format(*row))
	print()
	return rows

def patch_import():
	'''
	Import patch for current module if any.  
	Works only at program (re)start.  
	'''

	mod_name = inspect.currentframe().f_back.f_globals['__name__']
	patch = mod_name + '_patch'
	try:
		mdl = importlib.import_module(patch)
	except ModuleNotFoundError:
		return
	patch_items=[x for x in mdl.__dict__ if not x.startswith('__')]
	sys.modules[mod_name].__dict__.update(
		{k: getattr(mdl, k) for k in patch_items}
	)
	dev_print(
		f'patched {mod_name}, items: '
			+ ', '.join(patch_items)
	)

class DataHTTPReq(object):
	'''
	Browser request data as an object.
	'''
	def __init__(self, client_ip:str='', path:str=''
	, headers:dict={}, params:dict={}, method:str='GET'
	, form_data:dict={}, post_file:str='', body=None):
		'''
		*path* - '/task_name'
		*headers* - {"Accept-Encoding": "gzip, deflate", ...}
		*params* - URL parameters as a dictionary like {'par1': '123', ...}
		'''
		self.client_ip = client_ip
		self.path = path
		self.method:str = method
		self.body = body
		self.post_file = post_file
		self.host = ''
		self.accept = ''
		self.accept_encoding = ''
		self.accept_language = ''
		self.referer = ''
		self.headers = headers
		self.params = params
		self.form = form_data
		try:
			self.__dict__.update(form_data)
		except:
			dev_print('not a dict')
			pass

class DataBrowserExt(DataHTTPReq):
	'''
	HTTP request data helper for the 'SendToTaskopy'
	browser extension.
	'''
	def __init__(self):
		self.link_url:str = ''
		self.page_url:str = ''
		self.editable:bool = False
		self.media_type:str = ''
		self.src_url:str = ''
		self.selection:str = ''

def _etree_to_dict(tree: _ElementTree.ElementTree):
	di = {tree.tag: {} if tree.attrib else None}
	children = list(tree)
	if children:
		dd = defaultdict(list)
		for dc in map(_etree_to_dict, children):
			for k, v in dc.items():
				dd[k].append(v)
		di = {tree.tag: {k: v[0] if len(v) == 1 else v
					 for k, v in dd.items()}}
	if tree.attrib:
		di[tree.tag].update(('@' + k, v)
						for k, v in tree.attrib.items())
	if tree.text:
		text = tree.text.strip()
		if children or tree.attrib:
			if text:
			  di[tree.tag]['#text'] = text
		else:
			di[tree.tag] = text
	return di

def xml_to_dict(xml_str:str, remove_str:str=None)->tuple:
	'''
	Converts a XML to dictionary using lxml.etree
	Returns (True, dict) or (False, 'exception text')
	'''
	try:
		if remove_str: xml_str = xml_str.replace(remove_str, '')
		parser=lxml.etree.XMLParser(recover=True)
		tree = lxml.etree.fromstring(xml_str, parser=parser)
		return True, _etree_to_dict(tree)
	except Exception as e:
		dev_print(f'xml_str parsing error:\n\n{xml_str}\n\n')
		return False, repr(e)
_event_xmlns = ''
_REGEX_EVENT = re.compile(r'''(xmlns=('|").+?('|"))''')
def _xml_to_dict_event(event_xml:str)->tuple:
	''' Returns (True, dict) or (False, 'exception text') '''
	global _event_xmlns, _REGEX_EVENT
	if not _event_xmlns:
		_event_xmlns = _REGEX_EVENT.findall(event_xml)[0][0]
	return xml_to_dict(event_xml, remove_str=_event_xmlns)

def value_to_str(value, sep:str='\n')->str:
	'''
		Convert simple data types (str, dict, list, tuple)
		to a string.
	'''
	if isinstance(value, (str, int, float, type(None)) ): return str(value)
	strings = []
	if isinstance(value, dict):
		strings.append( value_to_str(tuple(value.values())) )
	elif isinstance(value, (list, tuple, set)):
		strings.extend((value_to_str(i) for i in value))
	return sep.join(strings)

class DataEvent:
	'''
	Windows event as an object.
	
	*EventData* can be a string, a dictionary or a list.

	*_EventDataDict* is an ugly data converted from XML.

	'''
	{
		'{http: //schemas.microsoft.com/win/2004/08/events/event}Event': {
			'System': {
				'Provider': {
					'value': ''
					, 'attrib': {
						'Name': 'Microsoft-Windows-DistributedCOM'
						, 'Guid': '{1B562E86-B7AA-4131-BADC-B6F3A001407E}'
						, 'EventSourceName': 'DCOM'
					}
				}
				, 'EventID': {
					'value': 10010
					, 'attrib': {'Qualifiers': '0'}
				}
				, 'Version': {'value': 0, 'attrib': {} }
				, 'Level': {'value': 2, 'attrib': {} }
				, 'Task': {'value': 0, 'attrib': {} }
				, 'Opcode': {'value': 0, 'attrib': {} }
				, 'Keywords': {'value': '0x8080000000000000', 'attrib': {} }
				, 'TimeCreated': {
					'value': ''
					, 'attrib': {'SystemTime': '2021-02-10T12:24:20.581005200Z'}
				}
				, 'EventRecordID': {'value': 729301, 'attrib': {} }
				, 'Correlation': {'value': '', 'attrib': {} }
				, 'Execution': {
					'value': ''
					, 'attrib': {'ProcessID': '952', 'ThreadID': '41804'}
				}
				, 'Channel': {'value': 'System', 'attrib': {} }
				, 'Computer': {'value': 'DB', 'attrib': {} }
				, 'Security': {'value': '', 'attrib': {'UserID': 'S-1-5-20'} }
			}
			, 'EventData': {
				'Data': {
					'value': '{AAC1009F-AB33-48F9-9A21-7F5B88426A2E}'
					, 'attrib': {'Name': 'param1'}
				}
			}
		}
	}

	def __init__(self, xml_str:str):
		r'''
		di_sys:
		{'Provider': {'@Name': 'LsaSrv',
			'@Guid': '{199fe037-2b82-40a9-82ac-e1d46c792b99}',
			'@EventSourceName': 'LsaSrv'},
			'EventID': {'@Qualifiers': '0', '#text': '6041'},
			'Version': '0',
			'Level': '2',
			'Task': '0',
			'Opcode': '0',
			'Keywords': '0x80000000000000',
			'TimeCreated': {'@SystemTime': '2021-02-09T10:42:57.000000000Z'},
			'EventRecordID': '89369733',
			'Correlation': None,
			'Execution': {'@ProcessID': '0', '@ThreadID': '0'},
			'Channel': 'System',
			'Computer': 'pc',
			'Security': None}
		'''
		ATTRS = ['Provider', 'EventID', 'Level', 'Task'
		, 'TimeCreated', 'EventRecordID', 'Channel'
		, 'Computer', 'Security']
		
		status, full_dict = _xml_to_dict_event(xml_str)
		if not status:
			return
		di_sys = full_dict.get('Event', {}).get('System')
		self.dict = full_dict
		self.Provider = di_sys.get('Provider', {}).get('@Name')
		self.EventID = 0
		self.Level = ''
		self.Task = 0
		self.TimeCreatedUTC = di_sys.get('TimeCreated', {})
		self.TimeCreatedLocal = 0
		self.EventRecordID = 0
		self.Channel = ''
		self.Computer = ''
		self.Security = None
		self.EventData = {}
		self.UserData = {}
		self.EventDataStr = ''
		self._EventDataDict = full_dict.get('Event', {}) \
			.get('EventData', {})
		for attr in ATTRS:
			if ( e := di_sys.get(attr, None) ):
				if isinstance(e, dict):
					setattr(
						self
						, attr
						, e.get('#text', getattr(self, attr, None) )
					)
				else:
					setattr(self, attr, e)
		if self.TimeCreatedUTC:
			ts = self.TimeCreatedUTC.get('@SystemTime', '.').split('.')[0]
			if ts:
				self.TimeCreatedUTC = datetime.datetime.fromisoformat(ts)
				self.TimeCreatedLocal = self.TimeCreatedUTC \
					+ datetime.timedelta(seconds= -time.timezone)
		for attr in ATTRS:
			if isinstance(v := getattr(self, attr, ''), str) \
			and v.isdigit():
				setattr(self, attr, int(v))
		if self.Channel == 'Security' and self._EventDataDict:
			for di in self._EventDataDict.get('Data', {}):
				self.EventData[di.get('@Name', '')] = di.get('#text', '')
		elif self._EventDataDict:
			try:
				edata = self._EventDataDict.get('Data')
				if isinstance(edata, dict):
					for elem in edata:
						if isinstance(elem, dict):
							data_name = elem.get('attrib', {}).get('Name', '')
							self.EventData[data_name] = elem.get('value', '')
						elif isinstance(elem, (dict, str)):
							self.EventData = elem
				elif isinstance(edata, (list, str)):
					self.EventData = edata
				else:
					self.EventData = str(edata)
			except Exception as e:
				dev_print(f'EventData exception: {repr(e)}')
				self.EventData = self._EventDataDict
		if self.EventData: self.EventDataStr = value_to_str(self.EventData)

def thread_start(func, args:tuple=(), kwargs:dict={}
, thr_daemon:bool=True, err_msg:bool=False, ident:str=''
, err_action=None)->int:
	'''
	Runs task in a thread. Returns thread id.  
	*ident* - user-defined identifier of stream.  
	*err_action* - function to run if an exception occurs.  
	The text of exception will be passed to the function.  

	'''
	def wrapper():
		nonlocal func, args, kwargs
		try:
			func(*args, **kwargs)
		except Exception:
			err_str = traceback.format_exc()
			tprint(
				f'exception in {func.__name__}:{str_indent(err_str)}'
			)
			if err_msg:
				warning(
					f'Exception in thread {func.__name__}:\n{err_str}'
				)
			if err_action:
				try:
					err_action(err_str)
				except:
					pass

	thr = threading.Thread(target=wrapper
	, daemon=thr_daemon)
	thr.start()
	if not tdebug():
		try:
			parents = _get_parents()
			parents.reverse()
			if ident: ident = ': ' + ident
			app.app_threads[thr.ident] = {
				'func': '>'.join(
					parents[-3:] if parents else ()
				) + '>' + func.__name__ + ident
				, 'stime': time_now()
				, 'thread': thr
			}
		except Exception as e:
			dev_print('thread_start save error: ' + repr(e))
			pass
	return thr.ident

task_run = thread_start

def app_threads_print():
	thread: threading.Thread
	table = [('ID', 'Daemon', 'Start time', 'Running time'
	, 'Target', 'Function')]
	for ident, thr_dic in app.app_threads.items():
		func_name = thr_dic.get('func')
		start_time = thr_dic.get('stime')
		run_time = time_diff_str(start_time) if start_time else None
		thread = thr_dic.get('thread', None)
		daemon = None
		target = None
		if thread != None:
			if not (is_alive := thread.is_alive()): continue
			daemon = thread.daemon
			target = getattr(thread, '_target', None)
			if target: target = getattr(target, '__name__', None)
		table.append((
			ident
			, daemon
			, str(start_time).split('.')[0]
			, run_time.split('.')[0]
			, target
			, func_name
		))
	dead = sum(1 for t in threading.enumerate() if not t.is_alive())
	table_print(table, use_headers=True, sorting=[2])
	tnum_sys = len(psutil.Process(pid=app.app_pid).threads())
	print('Number of threads:')
	print(f'table		{len(table) - 1}')
	print(f'dead		{dead}')
	print(f'threading	{len(threading.enumerate())}')
	print(f'system		{tnum_sys}\n')


def crontab_reload():
	' Reloads the crontab '
	return app.load_crontab()

def app_win_show():
	' Shows the application console window '
	app.show_window()

def app_dir()->str:
	' Returns current working directory '
	return app.dir

def app_tasks()->dict:
	' Returns dictionary with tasks '
	return app.tasks

def app_exit(force:bool=False):
	'''
	Closes the program.  
	*force* - do not wait for the completion
	of working tasks.  
	'''
	app.exit(force=force)

def benchmark(func, b_iter:int=1000
, a:tuple=(), ka:dict={})->int:
	'''
	Run function `func` `b_iter` times and print time.
	Returns nanoseconds per loop.
	Example:

		tass( benchmark(dir_size, 5, a=('logs',) ) , 70000, '<' )
	
	'''
	start = time.perf_counter_ns()
	if not is_iter(a): a = (a,)
	assert isinstance(ka, dict), 'ka should be a dictionary'
	for _ in range(b_iter):
		func(*a, **ka)
	total_ns = time.perf_counter_ns() - start
	ns_loop_str = '{:,}'.format(total_ns // b_iter).replace(',', ' ')
	ns_total_str = '{:,}'.format(total_ns).replace(',', ' ')
	name = ''
	if not func.__name__.startswith('<'):
		name = func.__name__ + ': '
	tdebug(f'{name}{ns_loop_str} ns/loop, total={ns_total_str}, {b_iter=}')
	return total_ns // b_iter

def median(source):
	return statistics.median(source)

def speak(text:str, wait:bool=False):
	'''
	Pronouns text using the Windows built-in speech engine.
	'''

	def _speak():
		nonlocal text
		pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
		speaker = win32com.client.Dispatch('SAPI.SpVoice')
		try:
			speaker.Speak(text)
		except pywintypes.com_error as e:
			dev_print(f'speaker error: {e}')
		pythoncom.CoUninitialize()
	
	if wait:
		_speak()
		return
	thread_start(_speak)

def func_name_human(func_name:str)->str:
	'''
	Converts function name from crontab to a "human" name.

	func_name_human('my_function')
	>'My function'

	func_name_human('My_Function')
	>'My Function'

	func_name_human('My__Function')
	>'My Function'

	'''
	new_name = func_name.replace('__', '_').replace('_', ' ')
	if new_name and new_name[0].isupper(): return new_name
	return new_name.capitalize()

def is_iter(obj, and_not_str:bool=True)->bool:
	'''
	Is the object iterable?  
	*and_not_str* - exclude strings.

		tass(is_iter('a'), False)
		tass(is_iter('a', and_not_str=False), True)
		tass(is_iter((1, 2)), True)
		mapobj = map(str, (1, 2))
		tass(is_iter(mapobj), True)
		tass(tuple(mapobj), ('1', '2'))
		tass(is_iter(1), False)

	'''
	if and_not_str and isinstance(obj, str): return False
	try:
		iter(obj)
		return True
	except TypeError:
		return False
	except:
		raise

class lazy_property(object):
	'''
	meant to be used for lazy evaluation of an object attribute.
	property should represent non-mutable data, as it replaces itself.
	'''
	def __init__(self, fget):
		self.fget = fget
		functools.update_wrapper(self, fget)

	def __get__(self, obj, cls):
		if obj is None:
			return self

		value = self.fget(obj)
		setattr(obj, self.fget.__name__, value)
		return value

def tass(value, expect, comp:str='=='):
	'''
	Assertion showing the difference.  
	Examples:

		tass(APP_NAME, 'Taskopy')

	'''
	if comp == '==':
		if value == expect:
			if type(value) == type(expect):
				return
			else:
				raise Exception(
					f'types are different:'
					+ f' {type(value)} vs {type(expect)}'
				)
	elif comp == '>':
		if value > expect: return
	elif comp == '<':
		if value < expect: return
	else:
		raise Exception('Unknown comp')
	raise Exception(f'does not match ({comp}):\nval: «{value}»\nexp: «{expect}»')

def exc_text(last_n:int=3, indent:bool=False):
	'''
	Get exception text.  
	*last_n* - the number of lines of the exception
	text from the end. *0* - get all.  
	Example:

		try:
			raise ZeroDivisionError('Just a test')
		except:
			dialog(exc_text())

	'''
	lines = traceback.format_exc().splitlines()
	if indent:
		return str_indent( '\n'.join(lines[-last_n:]) )
	else:
		return '\n'.join(lines[-last_n:])

def str_indent(src_str:str, prefix:str='    '
, borders:bool=True)->str:
	r'''
	Adds an indent to each line of text.  
	Example:

		try:
			raise ZeroDivisionError
		except:
			tprint('we have an error:' + str_indent(exc_text()))

	'''
	lines = str(src_str).strip().splitlines()
	tsize = os.get_terminal_size().columns - len(prefix) - 1
	wrap_lines = []
	for line in lines:
		if len(line := line.rstrip()) <= tsize:
			wrap_lines.append(line)
			continue
		for i in range(0, len(line), tsize):
			wrap_lines.append(line[i:i+tsize])
	tsize += len(prefix)
	return (
		('\n' + ('_' * tsize) if borders else '')
		+ '\n\n' + prefix
		+ ('\n' + prefix).join(wrap_lines) + '\n'
		+ ('_' * tsize if borders else '')
	)


def str_diff(text1:str, text2:str)->Tuple[Tuple[str]]:
	r'''
	Returns the different lines between two texts (strings with
	**line breaks**) as a tuple of tuples.

		tass(
			tuple(str_diff('foo\nbar', 'fooo\nbar'))
			, (('foo', 'fooo'),)
		)
		tass( tuple(str_diff('same\r\nlines', 'same\nlines') ), () )
		tass( tuple(str_diff('same\nlines', 'lines\nsame') ), () )

	'''
	lines1 = tuple(l.strip() for l in text1.splitlines() )
	lines2 = tuple(l.strip() for l in text2.splitlines() )
	diff1 = []
	diff2 = []
	for line in lines1:
		if not line or (line in lines2): continue
		diff1.append(line)
	for line in lines2:
		if not line or (line in lines1): continue
		diff2.append(line)
	return tuple(zip_longest(diff1, diff2, fillvalue=''))

def str_short(text:str, width:int=0, placeholder:str='...')->str:
	r'''
	Collapse and truncate the given text to fit in the given width.
	The text first has its whitespace collapsed.  If it then fits in
	the *width*, it is returned as is.  Otherwise, as many words
	as possible are joined and then the placeholder is appended.  
	If *width* is not specified, the current terminal width is used.

		tass( str_short('Hello,  world! ', 13), 'Hello, world!' )
		tass( str_short('Hello,  world! ', 12), 'Hello,...' )
		tass( str_short('Hello\nworld! ', 12), 'Hello world!' )
		tass( str_short('Hello\nworld! ', 11), 'Hello...' )
		tass( benchmark(str_short, 100, 'Hello,  world! '), 60_000, '<')

	'''
	if width == 0: width = os.get_terminal_size().columns - 1
	return textwrap.shorten(text=text, width=width
	, placeholder=placeholder)

if __name__ != '__main__': patch_import()
