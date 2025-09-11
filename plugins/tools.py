import sys
import os
import gc
import time
import datetime
from datetime import datetime as dtime, timedelta as tdelta, timezone as tzone
import statistics
import pytz
import threading
import configparser
import psutil
import sqlite3
import subprocess
from win32process import GetCurrentProcessId as _GetCurrentProcessId
import win32evtlog
import win32gui
import win32con
import win32com.client
import win32clipboard
import win32security
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
import types
import pyperclip
import random
import functools
import importlib
import string
import difflib
import argparse
from typing import Callable, Iterable 
from dataclasses import dataclass, field, asdict
from queue import Queue, SimpleQueue
from itertools import zip_longest
import pythoncom
import wx
from collections import defaultdict
import lxml
import textwrap
import io
import unicodedata
import multiprocessing
from xml.etree import ElementTree as _ElementTree
import windows_toasts as wtoasts
try:
	import constants as tcon
except ModuleNotFoundError:
	import plugins.constants as tcon

APP_NAME = 'Taskopy'
APP_VERSION = 'v2025-09-11'
APP_FULLNAME = APP_NAME + ' ' + APP_VERSION
if getattr(sys, 'frozen', False):
	APP_PATH = os.path.dirname(sys.executable)
	os.chdir(APP_PATH)
	sys.path.append(APP_PATH)
else:
	APP_PATH = os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) )

APP_ICON = os.path.join(APP_PATH, r'resources\icon.png')
APP_ICON_DIS = os.path.join(APP_PATH, r'resources\icon_dis.png')
APP_ICON_ICO = os.path.join(APP_PATH, r'resources\icon.ico')
_app_log:list[tuple[str, str]] = []
_APP_LOG_LIMIT:int = 10_000
_SIZE_UNITS = {'tb': 1_099_511_627_776, 'gb': 1_073_741_824
, 'mb': 1_048_576, 'kb': 1024, 'b': 1}

_DEFAULT_INI = r'''[General]
language=en
editor=notepad.exe
hide_console=False

[HTTP]
server_ip=127.0.0.1
server_port=8275
white_list=127.0.0.1
'''
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
_TERMINAL_WIDTH = os.get_terminal_size().columns - 1
TASK_ATTR:str = '__is_task__'
if (lambda: False)(): gdic:dict = {}
_MAIN_PID = os.getpid()


class Settings:
	r'''
	Load global settings from *.ini* file.  
	Settings from all sections are collected.  
	'''
	def __init__(self, ini_file:str='settings.ini'
	, def_sett:tuple=()):
		config = configparser.ConfigParser()
		config.optionxform = str
		if not ini_file: return
		ini_fpath = os.path.join(APP_PATH, ini_file)
		try:
			with open(ini_fpath, 'tr', encoding='utf-8-sig') as f:
				config.read_file(f)
		except FileNotFoundError:
			_create_default_ini_file()
			config.read(r'settings.ini', encoding='utf-8-sig')
		for section in config._sections.values():
			for sett_name, sett_val in section.items():
				if sett_val.lower() in ('true', 'yes'):
					self.__dict__[sett_name] = True
				elif sett_val.lower() in ('false', 'no'):
					self.__dict__[sett_name] = False
				elif sett_val.isdigit():
					self.__dict__[sett_name] = int(sett_val)
				elif sett_val.replace('.', '', 1).isdigit():
					try:
						self.__dict__[sett_name] = float(sett_val)
					except:
						self.__dict__[sett_name] = sett_val
				else:
					self.__dict__[sett_name] = sett_val
		for setname, setval in def_sett:
			self.__dict__.setdefault(setname, setval)


class DictToObj:
	''' Converts dictionary to object.
		Convert back: use vars() built-in function.
	'''
	def __init__(self, di:dict):
		self.__dict__.update(di)

	def __getattr__(self, name):
		return 'DictToObj - unknown key'
	
	def __str__(self)->str:
		return (
			self.__class__.__name__ + '('
			+ ', '.join(f'{k}={v}' for k,v in vars(self).items())
			+ ')'
		)


class SuppressPrint:
	r'''
	Suppresses outputting anything to the console.  
	Usage:

		with SuppressPrint():

	'''
	def __init__(self, bypass:bool=False) -> None:
		self._bypass:bool=bypass

	def __enter__(self):
		if self._bypass: return
		self._original_stdout = sys.stdout
		sys.stdout = open(os.devnull, 'w')

	def __exit__(self, exc_type, exc_val, exc_tb):
		if self._bypass: return
		sys.stdout.close()
		sys.stdout = self._original_stdout




class TQueue(Queue):
	r'''
	A queue that sends everything to the consumer in a different thread.  

		q = TQueue()
		q.put(1)
		q.stop()

	'''
	def __init__(self, consumer:Callable=print, max_size:int=4096)->None:
		super().__init__(maxsize=max_size)
		self._stop_sentinel:object = object()
		self.consumer:Callable=consumer
		thread_start(func=self.consumer_thread
		, ident='TQueue: ' + consumer.__name__)
	
	def consumer_thread(self):
		while True:
			item = self.get()
			if item is self._stop_sentinel:
				return
			try:
				self.consumer(item)
			except:
				qprint(self.consumer.__name__, 'exception:', exc_text(3))
			self.task_done()
	
	def stop(self):
		' Stop consumer thread '
		self.put(self._stop_sentinel)
class _BmarkInt(int): pass


def value_to_unit(value, unit:str='sec', unit_dict:dict=None
, def_src_unit:str='sec')->float:
	r'''
	Converts a string with a number and unit of measure
	to the desired unit of measure.  
	Usage:

		asrt( value_to_unit('1 min', 'sec'), 60.0)
		asrt( value_to_unit('2m', 'sec'), 120.0)
		asrt( value_to_unit(3, 'sec'), 3.0)
		asrt( value_to_unit('1-3 sec ') in (1, 2, 3), True)
		asrt( bmark(value_to_unit, ('1 ms',)), 11_000 )

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
		value = value.lower()
		tdebug(value)
		if '-' in value:
			v, u = value.split()
			vmin, vmax = v.split('-')
			v = random.randint(int(vmin), int(vmax))
		else:
			v, u = value.split()
		return (int(v) * unit_dict[u]) / dst_coef
	elif any(i.isdigit() for i in value):
		v = ''.join(filter(str.isdigit, value))
		u = ''.join(filter(lambda v: not v.isdigit(), value))
		src_coef = unit_dict[u.lower()]
		return (int(v) * src_coef) / dst_coef
	else:
		raise Exception('Wrong value')

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
	r'''
	Get name of parent function if any.  

		from plugins.tools import _get_parent_func_name
		asrt( bmark(_get_parent_func_name), 6328 )
		
	'''
	EXCLUDE = ('wrapper', 'run_task', 'run', 'dev_print', 'tprint'
		, 'main', 'run_task_inner', 'popup_menu_hk'
		, 'MainLoop', 'catcher', 'run_code', 'mapstar'
		, 'run_ast_nodes', 'run_cell_async', 'run_cell'
		, 'interact')
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

_TASK_NAME_SKIP = {'tprint', 'dev_print', 'tdebug', 'con_log', 'dialog'
, 'msgbox', 'inputbox', 'file_dialog', 'dir_dialog', 'wrapper'
, 'run', '_bootstrap', '_bootstrap_inner'}

def task_name(is_human:bool=False)->str:
	r'''
	Gets the name of the task from which it was called.  

		asrt( bmark(task_name), 1500 )

	'''
	MAX_LVL = 30
	global _TASK_NAME_SKIP
	tname = ''
	first_name = ''
	try:
		tasks = set(app.tasks.task_dict.keys())
	except NameError:
		return ''
	except AttributeError:
		return '<console>'
	except:
		return ''
	for lvl in range(1, MAX_LVL):
		try:
			fn = sys._getframe(lvl).f_code.co_name
			if fn in tasks:
				tname = fn
				break
			if not first_name:
				if not fn in _TASK_NAME_SKIP: first_name = fn
		except ValueError:
			tname = first_name if first_name else APP_NAME
			break
	else:
		pass
	if is_human and tname: tname = tname.replace('_', ' ')
	return tname

def task_add(func):
	r'''
	Adds an attribute indicating that the function is a *task*.
	'''
	setattr(func, TASK_ATTR, True)
	return func



def sound_play(sound:str|tuple|list|set, wait=False):
	r'''
	Plays a *.wav* file. If *fullpath* is a folder, select a random file.  
	If fullpath is *Iterable*, select a random file from this list.  
	'''
	fpath = sound
	if is_iter(sound):
		fpath = random.choice(sound)
	elif os.path.isdir(sound):
		fpath = random.choice(glob.glob(sound + '\\*'))
	flags = winsound.SND_FILENAME
	if not wait: flags += winsound.SND_ASYNC
	winsound.PlaySound(fpath, flags=flags)

def dev_print(*msg, **kwargs):
	r'''
	For debug.

		asrt( bmark(lambda: dev_print('bench'), b_iter=3), 600_000 )
	
	'''
	if is_dev() or is_con(): tprint(*msg, **kwargs)

_is_dev_cache:bool|None = None

def is_dev()->bool:
	r'''
	Running in developer mode?

		asrt( bmark(is_dev), 455 )

	'''
	global _is_dev_cache
	if not _is_dev_cache is None: return _is_dev_cache
	try:
		_is_dev_cache = hasattr(sys, 'ps1') or app.cmd_args.dev
	except (NameError, AttributeError):
		_is_dev_cache = True
	return _is_dev_cache

def _log_file(msg:str, fname:str):
	r'''
	Append the string to a log file.  
	*fname* - log file name.  
	'''
	for _ in (1, 2):
		try:
			with open(f'{app.dir}\\log\\{fname}.log', 'ta+'
			, encoding='utf-8') as f:
				f.write(msg)
			return 
		except FileNotFoundError:
			os.makedirs( app.dir + '\\log' )
			continue
		except:
			qprint(f'logging to a file exception: {exc_text()}')
			return

def _tlog(now_msgs:tuple[dtime, tuple]):
	global _app_log
	msg = ' '.join(map(str, now_msgs[1]))
	_app_log.append((now_msgs[0].replace(microsecond=0).isoformat(), msg))
	del _app_log[:-_APP_LOG_LIMIT]
	msg = now_msgs[0].strftime(_LOG_TIME_FORMAT) + ' ' + msg + '\n'
	fname = now_msgs[0].strftime(sett.log_file_name)
	_log_file(msg=msg, fname=fname)

def tlog(*msgs):
	r'''
	Write the message to the log file only (no output to the console).  
	'''
	if is_con(): return
	try:
		app.que_log.put((dtime.now(), msgs))
	except NameError:
		print(
			time_str(template=tcon.DATE_STR_HUMAN)
			, f'[app not init]', ' '.join(map(str, msgs))
		)

def con_log(*msgs):
	r'''
	Outputs a message to the console and to a log file.  
	'''
	global _app_log
	msg = ' '.join(map(str, msgs))
	tprint(msg, tname='')
	tlog(msg)

def time_now_str(template:str=tcon.DATE_STR_FILE
, use_locale:str='C', timezone=None, **delta)->str:
	r'''
	Returns a string with current time.  

		asrt( bmark(time_now_str), 38339 )
	
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
, time_val:dtime=None
, use_locale:str='C', timezone=None)->str:
	r'''
	Returns time in the form of a string in specified locale.  
	Use datetime in `time_val`. How to get yesterday's date:  

		time_val = datetime.date.today() - datetime.timedelta(days=1)
		asrt( bmark(time_str), 43573 )

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

def time_now(**delta)->dtime:
	r'''
	Returns datetime object.  
	Use `datetime.timedelta` keywords to get different date/time.  
	Yesterday:

		time_now(days=-1)
		asrt( bmark(time_now), 1046 )
	
	Use `.replace` to remove part of datetime:

		time_without_microsec = time_now().replace(microsecond=0)

	'''
	if not delta: return datetime.datetime.now()
	return ( datetime.datetime.now() + datetime.timedelta(**delta) )

def time_from_str(date_string:str, template:str=tcon.DATE_STR_FILE
, use_locale:str='C')->dtime:
	r'''
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

def time_diff(start:dtime, end:dtime|None=None
, unit:str='sec')->int:
	r'''
	Returns difference between dates in units.  
	*start* and *end* should be in `datetime` format.  
	If no *end* is specified, the current time is used.  

		ts = datetime.datetime(2023, 10, 1, 19, 40, 6, 903000)
		te = datetime.datetime(2023, 10, 1, 20, 40, 6, 903000)
		asrt( bmark(time_diff, (ts, te)), 1400 )
	
	'''
	if not end: end = datetime.datetime.now()
	seconds = (end - start).total_seconds()
	coef = _TIME_UNITS.get(unit, 1000) / 1000
	return int(seconds // coef)

def time_diff_str(start:dtime
, end:dtime|None=None, str_format:str=''
, no_ms:bool=True)->str:
	r'''
	Returns time difference as a string like that:
	'5 days, 3:01:35.837127'  
	It is better to use `time_diff_human`.  

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

def time_diff_human(start:dtime|float|tdelta, end:dtime|None|float=None
, with_ms:bool=False, sep:str=':', short:bool|int=True)->str:
	r'''
	Returns time difference as a string like that:
	'6h:54m'  
	Rationale: values like '5:45' are not as easy to read.
	Is it 5 hours and 45 minutes or 5 minutes and 45 seconds?  

	*end* - if omitted, use the current time.  
	*start* and *end*: *datetime* or timestamp as float.  
	*with_ms* - include milliseconds in the result.  
	*short* - only first two units otherwise full like '6h:54m:30s:673ms'  

		tn = dtime.now()
		asrt( bmark( time_diff_human, (tn,) ), 3_000 )

	'''
	delta:tdelta
	if isinstance(start, datetime.timedelta):
		delta = start
	else:
		if isinstance(start, float): start = dtime.fromtimestamp(start)
		if end == None:
			end = dtime.now()
		elif isinstance(end, float):
			end = dtime.fromtimestamp(end)
		delta = end - start
	is_negative = delta.total_seconds() < 0
	if is_negative: delta = -delta
	microseconds = delta.microseconds
	total_seconds = int(delta.total_seconds())
	days = total_seconds // (24 * 3600)
	total_seconds %= (24 * 3600)
	hours = total_seconds // 3600
	total_seconds %= 3600
	minutes = total_seconds // 60
	seconds = total_seconds % 60
	time_parts = []
	if days > 0: time_parts.append(f'{days}d')
	if hours > 0: time_parts.append(f'{hours}h')
	if minutes > 0: time_parts.append(f'{minutes}m')
	if seconds > 0: time_parts.append(f'{seconds}s')
	if with_ms: time_parts.append(f'{microseconds // 1000}ms')
	match short:
		case True:
			last = 2
		case False:
			last = len(time_parts)
		case _:
			last = short
	result = sep.join(time_parts[:last]) if time_parts else '0'
	if is_negative: result = '-' + result
	return result


def _date_part(date_val:dtime=None, part:str=''):
	if not date_val: date_val = datetime.datetime.now()
	return getattr(date_val, part)

def date_year(date_val:dtime=None)->int:
	'''Returns year'''
	return _date_part(part='year')

def date_month(date_val:dtime=None)->int:
	'''Returns month number'''
	return _date_part(part='month')

def date_day(date_val:dtime=None, delta:dict=None)->int:
	''' Returns current day of months (1-31) '''
	if not delta: return _date_part(part='day')
	if not date_val: date_val = datetime.datetime.now()
	return ( date_val + datetime.timedelta(**delta) ).day

def date_weekday(date_val:dtime|None=None, template:str='%A')->str:
	r'''
	Returns weekday as a string.  

		asrt( date_weekday(dtime(2023, 10, 1)), 'Sunday' )
		asrt( bmark(date_weekday, (dtime(2023, 10, 1),)), 8_000 )

	'''
	if date_val == None: date_val = datetime.date.today()
	return date_val.strftime(template)

def date_weekday_num(date_val:dtime=None)->int:
	r'''
	Weekday number (monday is 1).  
	*tdate* - `None` (today) or datetime.date(2019, 6, 12)

		asrt( date_weekday_num(datetime.date(2022, 9, 12) ), 1)

	'''
	if not date_val: date_val = datetime.date.today()
	return date_val.weekday() + 1

def date_fill(date_dic:dict, cur_date=None)->dtime:
	r'''
	Fills `None` values in dictionary with current
	datetime value.
	Example:

		dt_dic = {'year': None, 'month': 11
		, 'day': 31, 'hour': 23, 'minute': 24}
		date_fill(dt_dic)
		asrt( bmark(date_fill, a=(dt_dic,)), 8_000 )

	'''
	new_date_dic = {'year': 0, 'month': 0
	, 'day': 0, 'hour': 0, 'minute': 0}
	if cur_date == None: cur_date = datetime.datetime.now()
	for part in new_date_dic:
		if date_dic[part] == None:
			new_date_dic[part] = getattr(cur_date, part)
		else:
			new_date_dic[part] = date_dic[part]
	try:
		return datetime.datetime(**new_date_dic)
	except ValueError:
		new_date_dic['day'] = 28 
		return datetime.datetime(**new_date_dic)

def date_fill_str(date_str:str)->str:
	r'''
	Replace asterisk to current datetime value:  
	date_fill_str('*.*.01 12:30') -> '2020.10.01 12:30'

		asrt( bmark(date_fill_str, a=('*.*.01 12:30',)), 8_000 )

	'''
	if not '*' in date_str: return date_str
	date_str = date_str.replace('.', ' ').replace(':', ' ')
	new_date_lst = list( datetime.datetime.now().timetuple() )
	for pos, value  in enumerate( date_str.split() ):
		if value != '*': new_date_lst[pos] = value
	return '{:0>4}.{:0>2}.{:0>2} {:0>2}:{:0>2}' \
		.format(*new_date_lst)

def date_last_day_of_month(date:dtime)->dtime:
	' Returns last day of a month '
	if date.month == 12: return date.replace(day=31)
	return date.replace(month=date.month+1, day=1) - datetime.timedelta(days=1)

def time_sleep(interval:str|int|float|tuple, unit:str=''):
	r'''
	Pauses for specified amount of time.  
	*interval* - number of seconds (float) or `str` with unit like '5 min'
	or tuple with (start, stop) for random interval (you should
	provide unit in this case). Example:

		time_sleep( (2,10), 'sec' )
		time_sleep('2 sec')
	
	The minimum possible interval must be at least 2 milliseconds
	if the interval is specified by a string:

		asrt( bmark(time_sleep, a=('1 ms',)), 1_500_000 )
		# and for `interval` as a float:
		asrt( bmark(time_sleep, a=(0.000_001,)), 600_000 )
	
	`time.sleep` isn't that cheap on its own:

		asrt( bmark(lambda: None if False else time.sleep(0)), 3_000 )
		asrt( bmark(lambda: None if True else time.sleep(0)), 450 )

	'''
	if isinstance(interval, (int, float)) and not unit:
		time.sleep(interval)
		return
	elif isinstance(interval, (list, tuple)):
		interval = str( random_num(*interval) ) + ' ' + unit
	elif unit:
		interval = str(interval) + ' ' + unit
	time.sleep( value_to_unit(interval, 'sec') )
pause = time_sleep
wait = time_sleep

def clip_set(txt):
	r'''
	Поместите текст в текстовый буфер обмена.

		asrt( bmark(clip_set, ('test',), b_iter=3), 30_000_000 )
		
	'''
	pyperclip.copy(str(txt))

def clip_get()->str:
	r'''
	Returns the text from the clipboard, if any.

		asrt( bmark(clip_get), 30_000 )

	'''
	return pyperclip.paste()

def re_find(source:str, re_pattern:str, sort:bool=False
, unique:bool=False, re_flags:int=re.IGNORECASE)->list[str]:
	r'''
	Returns list with matches.  
	re_flags:  
	*re.IGNORECASE* - ignore case.  
	*re.MULTILINE* - make begin/end {^, $} consider each line.  
	*re.DOTALL* - make . match newline too.  
	*re.UNICODE* - make {\w, \W, \b, \B} follow Unicode rules.  
	*re.LOCALE* - make {\w, \W, \b, \B} follow locale.  
	*re.VERBOSE* - allow comment in regex.  

	Grouping:  
	Non-capturing group: (?:aaa)  
	Positive lookbehind: (?<=abc)  
	Negative lookbehind: (?<!abc)  
	'''
	matches = re.findall(re_pattern, source, flags=re_flags)
	if unique: matches = list(set(matches))
	if sort: matches.sort()
	return matches

def re_replace(source:str, re_pattern:str, repl:str=''
, re_flags:int=re.IGNORECASE)->str:
	r'''
	Regexp replace substring.  
	To use first group in `repl` use `\1`  
	'''
	return re.sub(
		pattern=re_pattern
		, repl=repl
		, string=source
		, flags=re_flags
	)

def re_split(source:str, re_pattern:str, maxsplit:int=0
, re_flags:int=re.IGNORECASE)->list[str]:
	'''
	Regexp split.
	
		asrt( re_split('abc', 'b'), ['a', 'c'] )
	
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

		asrt( re_match('C - 25.11.19.mp3', r'.+ - \d\d\.\d\d\.\d\d.+'), True )
		asrt( re_match('C - 25.11.19.mp3', r' - \d\d\.\d\d\.\d\d.+'), False)

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
		title = func_name_human(task_name())
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
				, ident='msgbox'
			)
			hwnd = get_hwnd(title_tmp)
			if hwnd:
				if dis_timeout:
					thread_start(dis_buttons, args=(hwnd, dis_timeout))
				thread_start(title_countdown, args=(hwnd, timeout, title)
				, ident=str_short('title_countdown: ' + msg, 40))
			while not result: time.sleep(0.01)
			if result:
				return result[0]
			else:
				return 0
		else:
			if dis_timeout:
				result = []
				thread_start(lambda *a, r=result: r.append(mb_func(*a))
				, args=mb_args, ident='msgbox')
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
					thread_start(title_countdown, args=(hwnd, timeout, title)
					, ident=str_short('title_countdown: ' + msg, 40))
			else:
				thread_start(mb_func, args=mb_args)
				hwnd = get_hwnd(title_tmp)
				if hwnd:
					win32gui.SetWindowText(hwnd, title)
					thread_start(title_countdown, args=(hwnd, timeout, title)
					, ident=str_short('title_countdown: ' + msg, 40))
		else:
			if dis_timeout:
				thread_start(mb_func, args=mb_args)
				hwnd = get_hwnd(title_tmp)
				if hwnd:
					win32gui.SetWindowText(hwnd, title)
					thread_start(dis_buttons, args=(hwnd, dis_timeout))
			else:
				thread_start(mb_func, args=mb_args)

def warning(msg:str, title:str='', timeout:str='30 min'):
	r'''
	Non-blocking error message.
	'''
	if not is_con():
		if sett.kiosk:
			con_log(f'warning: {msg}')
			return
	if title:
		title = f'{APP_NAME}: {title}'
	else:
		title = APP_FULLNAME
	dialog(msg=msg, timeout=timeout, icon_main=tcon.TD_ICON_ERROR
	, title=title, wait=False)

def _msg_err(msg:str, icon:int, title:str, parent:str, timeout:str):
	r'''
	Non-blocking error message.
	'''
	toast_imgs = {
		tcon.TD_ICON_WARNING: r'c:\Windows\System32\SecurityAndMaintenance_Alert.png'
		, tcon.TD_ICON_ERROR: r'c:\Windows\System32\SecurityAndMaintenance_Error.png'
	}
	if not is_con():
		try:
			if sett.kiosk:
				con_log(f'{parent}{" (" + title + ")" if title else ""}: {msg}')
				return
		except NameError:
			print(f'[no settings]: {msg}')
		except:
			raise
	if title:
		title = f'{APP_NAME}: {title}'
	else:
		title = APP_FULLNAME
	if sys_ver() >= 10.0:
		toast(msg=msg, img=toast_imgs.get(icon, '')
		, on_click=lambda c: app_win_show())
	else:
		dialog(msg=msg, timeout=timeout, icon_main=icon, title=title
		, wait=False)

def msg_err(msg:str, title:str='', source:str='', timeout:str='30 min'
, often_int:str='30 s'):
	r'''
	Reports important errors (exceptions). It outputs the full error
	text to the console, writes to the log and displays a message.  
	'''
	try:
		if is_often('__msg_err ' + source + msg, interval=often_int):
			if is_dev():
				tprint('error msg suppressed: ' + msg, tname=source
				, short=True)
			return
		exc_full:str=''
		exc_short:str=''
		try:
			exc_full, exc_short = exc_texts()
		except AttributeError:
			pass
		source = source if source else 'app'
		if exc_full:
			tprint(msg + str_indent(exc_full), tname=source)
			tlog(msg + str_indent(exc_full, borders=False))
		_msg_err(msg=msg + ' ' + exc_short, title=title
		, icon=tcon.TD_ICON_ERROR, timeout=timeout, parent='msg_err')
	except Exception as err:
		print(f'\n[msg_err] «{msg}» exception:\n\n{err}\n\n')
		_MessageBoxTimeout(None, 'msg_err exception', APP_NAME, 16
		, 0, 1_800_000)

def msg_warn(msg:str, title:str='', timeout:str='30 min'):
	r'''
	Reports non-critical errors. Outputs to the console
	and shows the message.
	'''
	tprint(msg)
	_msg_err(msg=msg, title=title, icon=tcon.TD_ICON_WARNING, timeout=timeout
	, parent='msg_warn')

def inputbox(message:str, title:str=None
, is_pwd:bool=False, default:str=''
, multiline:bool=False, topmost:bool=True)->str:
	r'''
	Request input from user.  
	*is_pwd* - use password dialog (hide input).
	Problem: don't use default or you will get this value
	whatever button user will press.
	'''
	if is_con():
		if is_pwd:
			return getpass.getpass(f'inputbox ({message}): ')
		else:
			return input(f'inputbox ({message}): ')
	if title == None:
		title = func_name_human(task_name())
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

_toast_app_icon = None
_toast_img_cache:dict = {}
def toast(msg:str|tuple|list, dur:str='default', img:str=''
, often_ident:str='', often_inter:str='30 sec', on_click:Callable=None
, appid:str=APP_NAME):
	r'''
	Windows toast notification.  
	*img* - full path to a picture.  
	*duration* - 'short'|'long'|'default'. 'default' and 'short' are the same?
	'long' is about 30 sec.  
	*on_click* - an action to perform on click. It is passed an
	argument with the click properties. If the notification has
	already disappeared from the screen and is in the action center
	, the action will be performed only if an valid *appid* is specified  
	*appid* - custom AppID. If you want toast to have the Taskopy icon, see the `emb_appid_add` task
	from *ext_embedded*.  

	Note: *winrt* works on Windows 10, October 2018 Update or later 
	'''
	global _toast_app_icon
	global _toast_img_cache
	OFTEN_IDENT_LEN = 10
	if sys_ver() < 10.0:
		dialog(msg=msg, wait=False, title='[Toast error]')
		return
	if dur == 'default': dur = 'Default'
	assert dur in ('Default', 'short', 'long'), 'wrong *dur* value'
	if on_click:
		assert len( func_arg(on_click) ) == 1, \
			'The `on_click` function must take 1 argument'
	if is_iter(msg):
		msg = list(str(m) for m in msg)
		if not often_ident: often_ident = msg[0]
	else:
		msg = [str(msg)]
		if not often_ident: often_ident = msg[0][:OFTEN_IDENT_LEN]
	if is_often('_toast ' + often_ident, interval=often_inter): return 'often'
	toaster = wtoasts.WindowsToaster(appid)
	newToast = wtoasts.Toast()
	newToast.duration = wtoasts.ToastDuration(dur)
	newToast.text_fields = msg
	if img:
		if (img_obj := _toast_img_cache.get(img)) is None:
			img_obj = wtoasts.ToastDisplayImage.fromPath(img)
			_toast_img_cache[img] = img_obj
		newToast.AddImage( img_obj )
	if on_click: newToast.on_activated = on_click
	try:
		toaster.show_toast(newToast)
	except OSError:
		dialog(msg=msg, wait=False, title='[Toast error]')



def file_dialog(title:str=None, multiple:bool=False
, default_dir:str='', default_file:str=''
, wildcard:str='', on_top:bool=True)->str|list[str]:
	''' Shows standard file dialog
		and returns fullpath or list of fullpaths
		if multiple == True.
		Will not work in console.
	'''

	def decap(s:str): return s[:1].lower() + s[1:] if s else ''

	if title == None:
		title = func_name_human(task_name())
	else:
		title = str(title)
	if is_con(): return input(f'File dialog ({title}): ')
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
		title = func_name_human(task_name())
	else:
		title = str(title)
	if is_con(): return input(f'Dir dialog ({title}): ')
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

def _create_default_ini_file():
	r'''
	Creates default settings.ini file.
	'''
	with open(os.path.join(APP_PATH, 'settings.ini'), 'xt'
	, encoding='utf-8-sig') as ini:
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
				qprint(job.error, job.result, job.time)
				
	'''
	pool = ThreadPool(pool_size)
	pool.map(lambda f: f(), (j.run for j in jobs))
	pool.close()
	pool.join()
	return jobs

class Job:
	r'''
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
				qprint('error:', job.result)
			else:
				qprint('result:', job.result)

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
		self.time:tdelta = None
		self.error = False
		self.job_name = job_name
	
	def run(self):
		time_start = time.time()
		try:
			self.result = self.func(*self.args, **self.kwargs)
			if isinstance(self.result, Exception):
				self.error = True
				self.result = f'exception: {repr(self.result)}' \
				+ f'\nat line {self.result.__traceback__.tb_lineno}'
		except:
			self.result = f'exception: {exc_text()}'
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
			qprint(job.error, job.result, job.time)
	
	'''
	job: Job
	for job in jobs:
		thread_start(job.run, ident='job: ' + job.func.__name__)
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

def qprint(*values):
	r'''
	Print to the console through a queue.  
	Intended to be used in place of the standard `print`.  
	Pros: non-blocking, FIFO.  

		asrt( bmark(print, ('a', 'b',), b_iter=3), 1_000_000 )
		asrt( bmark(qprint, ('a', 'b',), b_iter=3), 800_000 )

	'''
	msg = ' '.join(map(str, values))
	try:
		app.que_print.put(msg)
	except NameError:
		print(msg)
	except:
		print('<qprint fail>', msg)

def tprint(*msgs, tname:str|None=None, short:bool=False):
	r'''
	Prints the message(s) with the task name and time.  
	*tname* - name of the caller (task name). If it
	is `None`, then try to find the task name.  
	Use kwarg `short=True` to apply `str_short` to the output.  
	'''
	msg = ' '.join(map(str, msgs))
	if tname == None:
		if tname := task_name():
			if tname.startswith('<'):
				msg = ''.join((tname, ' ', msg))
			else:
				msg = ''.join(('[', tname, '] ', msg))
	else:
		if tname and (not tname.startswith('<')):
			msg = ''.join(('[', tname, '] ', msg))
	msg = ''.join((time.strftime('%y.%m.%d %H:%M:%S'), ' ', msg))
	if short:
		qprint( str_short(msg) )
	else:
		qprint(msg)

_is_con_cache:bool|None = None

def is_con()->bool:
	r'''
	Are we in the console?

		asrt( bmark(is_con), 500 )

	'''
	global _is_con_cache
	if not _is_con_cache is None: return _is_con_cache
	_is_con_cache = hasattr(sys, 'ps1')
	return _is_con_cache

def tdebug(*msgs, **kwargs)->bool:
	r'''
	Does the code execute from the console?  
	Use kwarg `short=True` to apply `str_short` to the output.  
	For paths better use `short=path_short`  

		asrt( bmark(tdebug), 600 )

	'''
	if not is_con(): return False
	if not msgs: return True
	short = kwargs.pop('short', False)
	sh_func = short if isinstance(short, Callable) else str_short
	msg:str = ''
	if kwargs.get('par', True):
		msg = task_name()
		if msg == '<console>': msg = ''
		if msg: msg = f'[{msg}]: '
	msg += ' '.join(map(str, msgs))
	qprint(sh_func(msg) if short else msg)
	return True

def balloon(msg:str, title:str=APP_NAME, timeout:int=None, icon:str=None):
	''' Show balloon. title - 63 symbols max, msg - 255.
		icon - 'info', 'warning' or 'error'.
	'''
	kwargs = {'title': title, 'text': msg}
	if is_con():
		tprint('<balloon>:', msg)
		return
	if timeout: kwargs['msec'] = timeout * 1000
	if icon:
		kwargs['flags'] = {
			'info': wx.ICON_INFORMATION
			, 'error': wx.ICON_ERROR
			, 'warning': wx.ICON_WARNING
		}.get(icon.lower(), wx.ICON_INFORMATION)
	app.taskbaricon.ShowBalloon(**kwargs)

def app_log()->list:
	r'''
	Returns current log as list of tuples with time:str and message:str  
	Log can't be empty.  
	'''
	return _app_log

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
	r'''
	Adds 'try... except' for function and returns
	(True, result) or (False, Exception).

	Downside: *iPython* autoreload does not
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
	r'''
	Evaluate function inside 'try... except'
	and return (True, <function result>)
	or (False, <Exception object>)

		asrt( bmark(lambda: None), 500 )
		asrt( bmark(safe(lambda: None)), 800 )

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
			if is_con(): tprint(f'<safe>: \n{trace_str}')
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
		_fields_ = [
			('hMainIcon', ctypes.wintypes.HICON)
			, ('pszMainIcon', ctypes.wintypes.LPCWSTR)
		]

	class DUMMYUNIONNAME2(ctypes.Union):
		_fields_ = [
			('hFooterIcon', ctypes.wintypes.HICON)
			, ('sFooterIcon', ctypes.wintypes.LPCWSTR)
		]

	_pack_ = 1
	_anonymous_ = (
		"DUMMYUNIONNAME",
		"DUMMYUNIONNAME2",
	)
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
	, buttons:Iterable|None=None
	, title:str=''
	, content:str=''
	, flags:int=0
	, common_buttons:int|None=None
	, default_button:int=0
	, timeout:str|int=0
	, return_button:bool=False
	, wait:bool=True
	, icon_main:int|None=None
	, icon_footer:int|None=None
)->int|str|tuple|None:
	r'''
	Shows dialog with multiple optional buttons.  
	Returns ID of selected button starting with 1000
	or `tcon.DL_TIMEOUT` if timeout is over.  
	*return_button* - returns tuple(status:bool, selected button value):  
		status == `True` if some of button was selected and 
		`False` if no button was selected (timeout or cancel).  
		You can use a dictionary as buttons, but then you have
		to distinguish the response from the `DL_TIMEOUT` or
		`DL_CANCEL` value yourself.  
	*wait* - non-blocking mode. It returns c_long object
	so it is possible to get user responce later with
	'.value' property (2 before user makes any choice)  
	*icon_main* - show icon. Note: the icon takes away horizontal
	space from the message text.  
	
	Note: do not start button text with new line (\\n) or dialog
	will fail silently.

		assert dialog(('y', 'n'), return_button=True) == (True, 'y')
		assert dialog({'y': 8, 'n': 9}) == 8
		assert dialog({'y': 8, 'n': 9}) == tcon.DL_CANCEL
		assert dialog({'y': 8, 'n': 9}, timeout='1 sec') == tcon.DL_TIMEOUT

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
				win32gui.SendMessage(hwnd, TDM_CLICK_BUTTON, None, None)
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
				except:
					raise Exception(f'dialog: wrong parameters ({exc_text()})')
		return S_OK
	if content: content = str(content)
	if title == '':
		title = func_name_human(task_name())
		title = title if title else APP_NAME
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
	if icon_main is None:
		if buttons and len(buttons) > 1:
			icon_main = tcon.TD_ICON_QUESTION
		else:
			icon_main = tcon.TD_ICON_INFORMATION
	tdc.hMainIcon = icon_main
	if icon_footer is None and timeout: icon_footer = tcon.TD_ICON_CROSS
	tdc.hFooterIcon = icon_footer
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
		_TaskDialogIndirect(ctypes.byref(tdc), ctypes.byref(result)
		, None, None)
	else:
		thread_start(_TaskDialogIndirect, args=(ctypes.byref(tdc)
		, ctypes.byref(result), None, None), ident='_TaskDialogIndirect')
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
	r'''
	Shows hint.  
	Returns PID of hint process.  
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
			, ident='hint: ' + text
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
	, use_headers:bool|tuple=False
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
	, max_table_width:int=0
	, trim_col:int=-1
	, trim_func=None
	, trim_placeholder:str='...'
):
	r'''
	Print list of lists/tuples as a table.

	*use_headers* - if it's True - takes first row as
	a headers. If it's list or tuple, then use this as
	a headers.  
	*sorting* - list of column numbers to sort by.  
	Example:  
	`sorting=[0, 1]` - sort table by first
	and second column  
	*sorting_func* - sort with this function.  
	*sorting_rev* - sort in reverse order.  
	*row_sep* - string to repeat as a row separator.  
	*headers_sep* - same for header(s).  
	*max_table_width* - maximum width of a table.  
	*trim_col* - number of the column (from 0) to be trimmed
	to meet the *max_table_width* constraint.
	The default (-1) is the last column.  
	*trim_func* - function to shorten a long string. If not
	set then `str_short` will be used. The function
	receives a string and its maximum length as an input.
	For full file paths it is better to use `path_short`  
	
	Example:

		table = [
			*(
				(random_num(1, 9_999), random_str(100), random_str(5))
				for _ in range(3)
			)
		]
		table_print(table, use_headers=('Header-1', 'Header-2', 'Header-3')
		, trim_col=1)

	'''

	DEF_SEP = '-'

	def print_sep(sep=row_sep):
		nonlocal table_width
		if not sep: return
		qprint( sep * (table_width // len(sep) ) )
	
	def print_headers(both=False):
		nonlocal headers, template
		if not headers: return
		if both: print_sep(sep=headers_sep)
		qprint(template.format(*headers))
		print_sep(sep=headers_sep)
	
	def trimmer(src_str:str, width:int
	, placeholder:str=trim_placeholder)->str:
		return str_short(text=src_str, width=width, placeholder=placeholder)

	if not table: return table
	headers = []
	if use_headers and not headers_sep: headers_sep = DEF_SEP
	if row_sep_step and not row_sep: row_sep = DEF_SEP
	if row_sep and not headers_sep: headers_sep = row_sep
	if isinstance(table, dict):
		rows = [list( di.values() ) for di in table.values()]
		if use_headers == True:
			headers = list(
				list( table.values() )[0].keys()
			)
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
				'table_print: the first row must be list of headers'
			)
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
	digital = []
	for col_num in range(len(rows[0])):
		col_values = (row[col_num] for row in rows[(1 if use_headers else 0):])
		if all(
			v in consider_empty or isinstance(v, (int, float))
			for v in col_values
		):
			digital.append(col_num)
	new_rows = []
	for row in rows:
		new_row = []
		for cell in row:
			if cell in consider_empty:
				cell = empty_str
			elif isinstance(cell, (int, float)):
				cell = '{:,}'.format(cell).replace(',', '_')
			else:
				cell = ' '.join( str(cell).splitlines() )
			new_row.append(cell)
		new_rows.append(new_row)
	rows = new_rows
	max_col_len = tuple( max( map(len, col) ) for col in zip(*rows) )
	table_width = sum(max_col_len) + len(col_pad) * (len(max_col_len) - 1)
	if not max_table_width:
		max_table_width = _TERMINAL_WIDTH
	if table_width > max_table_width:
		trim_len = 0
		if trim_col == -1: trim_col = len(rows[0]) - 1
		if not trim_func: trim_func = trimmer
		trim_len = (
			max_col_len[trim_col] - (table_width - max_table_width)
		)
		new_rows = []
		for row in rows:
			new_rows.append((
				*row[:trim_col]
				, trim_func(row[trim_col], trim_len)
				, *row[trim_col + 1:]
			))
		rows = new_rows
		max_col_len = tuple( max( map(len, col) ) for col in zip(*rows) )
		table_width = max_table_width
	template = col_pad.join([
		('{{:{}{}}}').format(('>' if n in digital else '<' ), s)
		for n, s in enumerate(max_col_len)
	])
	if headers: rows.pop(0)
	qprint()
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
		qprint(template.format(*row))
	qprint()

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

class lazy_property(object):
	'''
	Meant to be used for lazy evaluation of an object attribute.
	Property should represent non-mutable data, as it replaces itself.
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


class DataHTTPReq(object):
	r'''
	HTTP client request data.  
	'''
	def __init__(self, client_ip:str='', path:str=''
	, headers:dict={}, params:dict={}, method:str='GET'):
		r'''
		*path* -- '/task_name'
		*headers* -- {"Accept-Encoding": "gzip, deflate", ...}
		*params* -- URL parameters as a dictionary like {'par1': '123', ...}
		'''
		self.client_ip:str = client_ip
		self.path:str = path
		self.method:str = method
		self._file:str = ''
		self._body:bytes = b''
		self._fullpath:str = ''
		self.host:str = ''
		self._md5:str = ''
		self.accept:str = ''
		self.accept_encoding:str = ''
		self.accept_language:str = ''
		self.referer:str = ''
		self.headers:dict = headers
		self.params:dict = params
		self.form:dict = {}
	
	def _form_upd(self):
		try:
			self.__dict__.update(self.form)
		except:
			dev_print('DataHTTPReq: not a dict')
			pass
	
	@lazy_property
	def file(self)->str:
		if self._file:
			return self._file
		elif self.body:
			with open(self._fullpath, 'wb') as fd:
				fd.write(self.body)
			return self._fullpath
	
	@lazy_property
	def body(self)->bytes:
		if self._body: return self._body
		if self._file:
			with open(self._file, 'rb') as fd:
				return fd.read()
		return b''

	def __repr__(self) -> str:
		attrs = ', '.join(f'{k}={v!r}' for k, v in vars(self).items()
		if not k.startswith('_'))
		return f"{self.__class__.__name__}({attrs})"

	def __str__(self) -> str:
		return self.__repr__()

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
	r'''
	Converts a XML to dictionary using lxml.etree
	Returns (True, dict) or (False, 'exception text')
	'''
	try:
		if remove_str: xml_str = xml_str.replace(remove_str, '')
		parser=lxml.etree.XMLParser(recover=True)
		tree = lxml.etree.fromstring(xml_str, parser=parser)
		return True, _etree_to_dict(tree)
	except:
		dev_print(f'xml_str parsing error:\n\n{xml_str}\n\n')
		return False, exc_text()
_event_xmlns = ''
_REGEX_EVENT = re.compile(r'''(xmlns=('|").+?('|"))''')
def _xml_to_dict_event(event_xml:str)->tuple:
	''' Returns (True, dict) or (False, 'exception text') '''
	global _event_xmlns, _REGEX_EVENT
	if not _event_xmlns:
		_event_xmlns = _REGEX_EVENT.findall(event_xml)[0][0]
	return xml_to_dict(event_xml, remove_str=_event_xmlns)

def value_to_str(value, sep:str='\n')->str:
	r'''
	Converts simple data types (str, dict, list, tuple)
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
	r'''
	Windows event as an object.
	
	'''

	def __init__(self, event:list, msg:str, evt_data):
		r'''
		*event* - result of `win32evtlog.EvtRender`
		with `win32evtlog.EvtRenderEventValues`  
		'''
		self.activity_id = event[win32evtlog.EvtSystemActivityID][0]
		self.channel = event[win32evtlog.EvtSystemChannel][0]
		self.computer = event[win32evtlog.EvtSystemComputer][0]
		self.event_id = event[win32evtlog.EvtSystemEventID][0]
		self.event_record_id = event[win32evtlog.EvtSystemEventRecordId][0]
		self.keywords = event[win32evtlog.EvtSystemKeywords][0]
		self.level = event[win32evtlog.EvtSystemLevel][0]
		self.opcode = event[win32evtlog.EvtSystemOpcode][0]
		self.process_id = event[win32evtlog.EvtSystemProcessID][0]
		self.provider_guid = event[win32evtlog.EvtSystemProviderGuid][0]
		self.provider_name = event[win32evtlog.EvtSystemProviderName][0]
		self.qualifiers = event[win32evtlog.EvtSystemQualifiers][0]
		self.related_activity_id = event[win32evtlog.EvtSystemRelatedActivityID][0]
		self.task = event[win32evtlog.EvtSystemTask][0]
		self.thread_id = event[win32evtlog.EvtSystemThreadID][0]
		self.time_created = event[win32evtlog.EvtSystemTimeCreated][0]
		self.user_id = event[win32evtlog.EvtSystemUserID][0]
		self.version = event[win32evtlog.EvtSystemVersion][0]
		self.msg:str = msg
		self.event_data:list = [d[0] for d in evt_data]
	
	@lazy_property
	def time_created_local(self)->dtime:
		r'''
		From UTC to local time.  
		'''
		return self.time_created + tdelta(seconds=-time.timezone)
	
	@lazy_property
	def _user(self)->tuple:
		return win32security.LookupAccountSid(None, self.user_id)
	
	@lazy_property
	def user_name_short(self)->str:
		return self._user[0]

	@lazy_property
	def user_name_full(self)->str:
		return f'{self._user[1]}\\{self._user[0]}'

	@lazy_property
	def user_domain(self)->str:
		return self._user[1]

	def __repr__(self):
		attrs = ', '.join(f'{k}={v!r}' for k, v in vars(self).items())
		return f'{self.__class__.__name__}({attrs})'

def _thread_pop(src:str, thread_id:int):
	' Delete current thread from `app.app_threads` '
	thread = app.app_threads.pop(thread_id, None)
	if thread is None:
		pass
	else:
		del thread['thread']
		del thread

def thread_start(func, args:tuple=(), kwargs:dict={}
, is_daemon:bool=True, err_msg:bool=False, ident:str=''
, err_action:Callable|None=None)->threading.Thread:
	r'''
	Runs function in a thread. Returns thread object  
	*is_daemon* - thread runs in the background and is terminated
	automatically when the main program exits, regardless of whether
	the daemon thread has finished its work or not.  
	*ident* - user-defined identifier of thread.  
	*err_action* - function to run if an exception occurs.  
	The text of exception will be passed to the function.  

		asrt( bmark(thread_start, (lambda: None,)), 500_000 )
		asrt( bmark(threading.get_ident), 400 )

	'''
	
	def wrapper():
		nonlocal func, args, kwargs, thread
		try:
			app.app_threads[thread.ident] = {'func': ident
			, 'stime': dtime.now(), 'thread': thread}
		except NameError:
			pass
		try:
			func(*args, **kwargs)
		except:
			if err_msg:
				msg_err(f'Exception in a thread with «{func.__name__}»')
			if err_action:
				try:
					err_action(traceback.format_exc().strip())
				except Exception as err:
					if is_dev():
						tprint(f'exception in err_action: {repr(err)}')
		_thread_pop('thread_start', thread_id=thread.ident)

	def err_handler(text:str):
		if not is_dev(): return
		tprint(f'exception in thread «{ident}»: {str_indent(text)}'
		, tname='thread_start')

	if not ident:
		parents = list(reversed(_get_parents()))[-3:]
		parents.append(func.__name__)
		ident = '>'.join(parents)
	if err_action is None: err_action = err_handler
	thread = threading.Thread(target=wrapper, daemon=is_daemon
	, name=func.__name__)
	thread.start()
	return thread

def task_start(taskname:str|Callable, **kwargs):
	r'''
	Starts the task.  
	This is not just a matter of launching a function in a separate
	thread: related procedures are performed: checking if the task
	is running, checking the rules for launching the task, etc.  

	If all you want to do is just run the function in a separate thread
	, see `thread_start`.

	Note: You can only use *task options* in *kwargs*
	'''
	if isinstance(taskname, Callable): taskname = taskname.__name__
	for tname, tdic in app.tasks.task_dict.items():
		if taskname == tname: break
	else:
		raise Exception('Task not found')
	app.tasks.run_task(tdic, **kwargs)

def app_threads_print():
	thread: threading.Thread
	table = [('TID', 'Dmn', 'Start time', 'Running time'
	, 'Target', 'Identity')]
	for ident, thr_dic in tuple(app.app_threads.items()):
		func_name = thr_dic.get('func')
		start_time = thr_dic.get('stime')
		run_time = time_diff_human(start_time, short=True) \
			if start_time else None
		thread = thr_dic.get('thread')
		if thread is None:
			table.append((
				ident
				, '?'
				, str(start_time).split('.')[0]
				, run_time
				, '?'
				, func_name
			))
			continue
		is_daemon = thread.daemon
		target = getattr(thread, '_target', None)
		if target: target = getattr(target, '__name__', None)
		table.append((
			ident
			, 'D' if is_daemon else '-'
			, str(start_time).split('.')[0]
			, run_time
			, target
			, func_name
		))
	tnum_thread = 0
	tnum_dead = 0
	for t in threading.enumerate():
		tnum_thread += 1
		if not t.is_alive(): tnum_dead += 1
	tnum_sys = len(psutil.Process(pid=app.app_pid).threads())
	tnum_app = len(app.app_threads)
	table_print(table, use_headers=True, sorting=[2]
	, trim_func=path_short)
	qprint('Number of threads:')
	qprint(f'app		{tnum_app} (dead {tnum_dead})')
	qprint(f'threading	{tnum_thread} ({tnum_thread - tnum_app})')
	qprint(f'system		{tnum_sys} ({tnum_sys - tnum_app})\n')

def crontab_reload():
	' Reloads the crontab '
	return app.load_crontab()

def app_win_show():
	r'''
	Bring the application console window to the foreground, if possible.
	'''
	if is_con(): return
	app.show_window()

def app_dir()->str:
	r'''
	Returns the application directory without the trailing slash.

		asrt( bmark(app_dir), 2000 )
		
	'''
	if is_con(): return os.getcwd()
	return app.dir

def app_tasks()->dict[str, dict]:
	r'''
	Returns dictionary with tasks. Keys are function names
	, and values are a dictionary with all the properties of a task.  
	'''
	return app.tasks.task_dict

def app_enable():
	r'''
	Enabling the application
	'''
	app.taskbaricon.on_disable(state=True)

def app_disable():
	r'''
	Disabling the application. You can still start a task
	via the icon menu.  
	'''
	app.taskbaricon.on_disable(state=False)

def app_exit(force:bool=False):
	r'''
	Close the application.  
	*force* - do not display a warning dialog about running tasks.  
	'''
	app.taskbaricon.on_exit(force=force)

def app_restart(force:bool=False):
	r'''
	Restart the application.  
	*force* - do not display a warning dialog about running tasks.  
	'''
	app.taskbaricon.on_restart(force=force)

def app_pid()->int:
	r'''
	Returns current PID.

		asrt( bmark(app_pid), 500 )

	'''
	return _MAIN_PID

def bmark(func, a:tuple=(), ka:dict={}, b_iter:int=10
, do_print:bool=True)->int:
	r'''
	Runs the `func` `b_iter` times and returns the number of
	nanoseconds per cycle.  
	Example:

		asrt( bmark(lambda i: i+1, a=(1,), b_iter=10 ) , 2_000 )
		asrt( bmark(time.perf_counter_ns), 500 )
		# median=400 ns/loop, best=400, worst=1_400, total=5_100, 10 loops
	
	'''
	
	def arg_to_str(arg)->str:
		if isinstance(arg, (int, float)):
			return(str(arg))
		elif isinstance(arg, (str, datetime.datetime)):
			return(repr(arg))
		elif isinstance(arg, (tuple, list, set)):
			if isinstance(arg, tuple):
				bs, be = '(', ') '
			elif isinstance(arg, list):
				bs, be = '[', ']'
			else:
				bs, be = '{', '}'
			return f'{bs}{", ".join(arg_to_str(a) for a in arg)}{be}'
		elif isinstance(arg, dict):
			return '{' + ', '.join(
				f'{arg_to_str(k)}: {arg_to_str(v)}' for k,v in arg.items()
			) + '}'
		elif isinstance(arg, types.FunctionType):
			return arg.__name__
		elif arg is None:
			return 'None'
		elif isinstance(arg, Callable):
			return arg.__name__
		else:
			raise Exception(f'Unknown arg type: {type(arg)}')
	ASRT_COEF = 1.1
	if not is_iter(a): a = (a,)
	assert isinstance(ka, dict), '*ka* should be a dictionary'
	timings:list = []
	for _ in range(b_iter):
		start = time.perf_counter_ns()
		func(*a, **ka)
		timings.append(time.perf_counter_ns() - start)
	ns_median:int = int(median(timings))
	name = func.__name__
	if do_print:
		ns_max = max(timings)
		qprint(
			'median={} ns/loop, best={}, worst={}, total={}, {} loops'.format(
				*map(int_str, (
					ns_median, min(timings), ns_max, sum(timings), b_iter
				))
			)
		)
		args = []
		for arg in a: args.append(arg_to_str(arg))
		args = f", ({', '.join(args)},)" if args else ''
		round_digit = len(str(ns_median)) - 2
		qprint(f'asrt( bmark({name}{args})'
		+ f", {int_str(round(ns_median * ASRT_COEF, -round_digit))} )")
	return _BmarkInt(ns_median)

def median(source):
	r'''
	Returns `int` or `float` depending on the data.  
	Will generate an error if the *source* is empty.  
	Examples:

		asrt( median((1, 3, 5)), 3)
		asrt( median([1, 3]), 2.0)

	'''
	return statistics.median(source)

def speak(text:str, wait:bool=False):
	r'''
	Pronouns text using the Windows built-in speech engine.  
	If *wait* then returns *text*.  
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
	
	text = str(text)
	if wait:
		_speak()
		return text
	thread_start(_speak, ident='speak «' + str_short(text, 30) + '»')

def func_name_human(func_name:str)->str:
	r'''
	Converts function name from crontab to a "human" name.

		asrt( func_name_human('my_function'), 'My function' )
		asrt( func_name_human('My_Function'), 'My Function' )
		asrt( func_name_human('My__Function'), 'My Function')

	'''
	new_name = func_name.replace('__', '_').replace('_', ' ')
	if new_name and new_name[0].isupper(): return new_name
	return new_name.capitalize()

def is_iter(obj, and_not_str:bool=True)->bool:
	'''
	Is the object iterable?  
	*and_not_str* - exclude strings.

		asrt(is_iter('a'), False)
		asrt(is_iter('a', and_not_str=False), True)
		asrt(is_iter((1, 2)), True)
		mapobj = map(str, (1, 2))
		asrt(is_iter(mapobj), True)
		asrt(tuple(mapobj), ('1', '2'))
		asrt(is_iter(1), False)

	'''
	if and_not_str and isinstance(obj, str): return False
	try:
		iter(obj)
		return True
	except TypeError:
		return False
	except:
		raise

def asrt(value, expect, comp:str='==', show_diff:bool=False):
	r'''
	Assertion showing the difference.  
	Examples:

		asrt(APP_NAME, 'Taskopy')

	'''
	if comp == '<' or isinstance(value, _BmarkInt):
		if value < expect: return
		comp = '<'
	elif comp == '==':
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
	else:
		raise Exception('Unknown comp')
	diff_str:str = ''
	diff_num:int = 0
	if show_diff:
		expect = str(expect)
		value = str(value)
		for num, char in enumerate(value):
			if expect[num] != char:
				diff_num = num
				diff_str = ' at ' + str(diff_num)
				break

	msg = 'does not match ({comp}){diff_str}:\nval: «{value}»' \
		+ '{num_pos}\nexp: «{expect}»'
	value_str = str(value)
	expect_str = str(expect)
	if isinstance(value, str): value_str = repr(value)[1:-1]
	if isinstance(expect, str): expect_str = repr(expect)[1:-1]
	msg = msg.format(
		comp=comp
		, diff_str=diff_str
		, value=value_str
		, num_pos=('\n' + ' ' * (diff_num + 6) + '↕') if show_diff else ''
		, expect=expect_str
	) 
	raise Exception(msg)

def exc_text(line_num:int=1, with_file:bool=True)->str:
	r'''
	Gets the shorted text of an exception.  
	*line_num* - the number of lines of the exception
	text from the end. *0* - get all.  
	
	Rationale: because of the heavy use of the win32 api
	, these win32 exceptions should be handled differently.  

	Example:

		try:
			raise ZeroDivisionError('Just a test')
		except:
			dialog(exc_text())

	'''
	if line_num > 1:
		lines = traceback.format_exc().splitlines()
		return '\n'.join(lines[-line_num:])
	exc_type, exc_value, exc_tb = sys.exc_info()
	last_frame = traceback.extract_tb(exc_tb)[-1]
	del exc_tb
	fullpath = last_frame.filename
	lineno = last_frame.lineno
	function = last_frame.name
	exc_name = exc_type.__name__
	fname:str = ''
	if with_file: fname = os.path.basename(fullpath)
	if isinstance(exc_value, pywintypes.error):
		msg = f'{function}: {exc_value.strerror.rstrip(".")}' \
		+ f' ({exc_value.winerror})'
		if with_file: msg += f' at line {lineno} in file {fname}'
		return msg
	if with_file:
		return f'{exc_name} at line {lineno} in file {fname}'
	else:
		return f'{exc_name} at line {lineno}'



def exc_texts()->tuple[str, str]:
	r'''
	Returns the full and short texts of an exception.

		try:
			raise ZeroDivisionError
		except:
			f, s = exc_texts()
			qprint('short:', s)
			qprint('full:', f)

	'''
	return traceback.format_exc().strip(), exc_text()

def exc_name()->str:
	r'''
	Returns exception name only:

		try:
			0 / 0
		except:
			asrt(exc_name(), 'ZeroDivisionError')

		asrt( bmark(exc_name), 800 )
	
	'''
	ex_class = sys.exc_info()[0]
	return ex_class.__name__ if ex_class else ''

def int_str(value, sep:str='_')->str:
	r'''
	Convert a number to a string with the specified thousandth separator.

		asrt( bmark(int_str, (1024,), b_iter=3), 4_000)

	'''
	return '{:,}'.format(int(value)).replace(',', sep)

def str_indent(src_str, prefix:str='    '
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
	tsize = _TERMINAL_WIDTH - len(prefix)
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


def str_diff(text1:str, text2:str, context:tuple=(5, 70)
, ignore_whitespace:bool=True, diff_threshold:int=3)->list[tuple[str, str]]:
	r'''
	Returns the differences between two texts as a list with tuples of
	strings. The differences are given within a context of the
	specified size.  
	*context* - the first number is the number of characters before
	the difference, and the second number is the total length of the context.
	A long context can include several differences.
		text1 = 'This is a simple test where we compare two strings.' \
			+ ' These strings may not have punctuation.'
		text2 = 'This is a simple test where we compare several strings.' \
			' The strings may not contain punctuation.'
		asrt(
			str_diff(text1, text2, context=(3, 55))
			, [(
				're two strings. These strings may not have punctuation.',
				're several strings. The strings may not contain punctua'
			)]
		)
		asrt(
			str_diff(text1, text2, context=(3, 20))
			, [
				('re two strings. Thes', 're several strings. ')
				, (' These strings may n', ' The strings may not')
				, ('ot have punctuation.', 'ot contain punctuati')
			]
		)
		asrt(
			str_diff(text1, text2, context=(0, 0))
			, [('two', 'several'), ('es', ''), ('have', 'contain')]
		)
		asrt( str_diff('last', 'last1'), [('last', 'last1')] )
		asrt( str_diff('1first', 'first'), [('1first', 'first')] )
		asrt( str_diff('context', 'context1'), [('ntext', 'ntext1')] )

		asrt(
			bmark(str_diff, (random_str(), random_str(),))
			, 21_000_000
		)

	'''
	if ignore_whitespace:
		text1 = ' '.join(text1.split())
		text2 = ' '.join(text2.split())
	diff = list(difflib.ndiff(text1, text2))
	diff_len:int = len(diff)
	diff_nums:list = []
	diff_with_context:list = []
	start:int = -1
	end:int = 0
	for num, line in enumerate(diff):
		if line.startswith('+') or line.startswith('-'):
			if start == -1: start = num
			if num < (diff_len - 1): continue
		if (line.startswith(' ') or num == (diff_len - 1)) and start > -1:
			break_flag:bool = False
			for thresh in reversed(range(diff_threshold + 1)):
				if (num + thresh) < (diff_len - 1):
					if any(
						not d.startswith(' ') for d in diff[num:num+thresh]
					):
						tdebug(
							'skip an unimportant match at', num
							, ': "'+ ''.join(d[2:]
								for d in diff[num:num+thresh]) + '"'
						)
						break_flag = True
						break
			tdebug(start, num)
			if break_flag: continue
			diff_nums.append((start, num))
			start = -1
	if is_con() and len(diff) < 100:
		qprint('\n'.join(f'{n}: {l}' for n, l in enumerate(diff) ))
	tdebug(f'nums ({len(diff_nums)}):', ', '.join(f'{n[0]}-{n[1]}'
		for n in diff_nums))
	cut_end:int = 0
	context_beg:int = context[0]
	context_length:int = context[1]
	for start, end in diff_nums:
		if cut_end and end < cut_end:
			tdebug(f'skip overlaped {end=}, {cut_end=}')
			continue
		subs1 = ''
		subs2 = ''
		cut_end:int = end
		for line in diff[start:end]:
			if line.startswith('+'):
				subs2 += line[2:]
			elif line.startswith('-'):
				subs1 += line[2:]
			else:
				subs1 += line[2:]
				subs2 += line[2:]
		tdebug(f'{subs1=}, {subs2=}')
		subs1_len:int = len(subs1)
		subs2_len:int = len(subs2)
		if context_length > max(subs1_len, subs2_len):
			short1:int = context_length - subs1_len
			short2:int = context_length - subs2_len
			if short1 > 1:
				end_len:int=0
				beg_len = min(short1, context_beg)
				if short1 > beg_len: end_len = short1 - beg_len
				count:int = 0
				if start:
					for line in diff[start - 1::-1]:
						if not line.startswith('+'):
							subs1 = line[2:] + subs1
							count += 1
							if count == beg_len: break
				count = 0
				if end_len:
					for line in diff[end:]:
						if not line.startswith('+'):
							subs1 += line[2:]
							count += 1
							if count == end_len: break
				cut_end = end + end_len
			if short2 > 1:
				end_len:int=0
				beg_len = min(short2, context_beg)
				if short2 > beg_len: end_len = short2 - beg_len
				count:int = 0
				if start:
					for line in diff[start - 1::-1]:
						if not line.startswith('-'):
							subs2 = line[2:] + subs2
							count += 1
							if count == beg_len: break
				count = 0
				if end_len:
					for line in diff[end:]:
						if not line.startswith('-'):
							subs2 += line[2:]
							count += 1
							if count == end_len: break
				cut_end = min(cut_end, end + end_len)
		tdebug(f'{start=}, {end=}, {cut_end=}, {subs1_len=}, {subs2_len=}')
		tdebug('1: "' + subs1 + '"')
		tdebug('2: "' + subs2 + '"')
		tdebug('_' * context_length)
		if ignore_whitespace and subs1.isspace() and subs2.isspace(): continue
		diff_with_context.append((subs1, subs2))
	return diff_with_context
def str_short(text:str, width:int=0, placeholder:str='...'
, whitespace:str=string.whitespace)->str:
	r'''
	Collapse and truncate the given text to fit in the given width.  
	The main purpose is to shorten text for output to the console
	so extra whitespace characters are removed, including line breaks.  
	If *width* is not specified, the current terminal width is used.  
	For full file paths it is better to use `path_short`  

		asrt( str_short('Hello,  world! ', 13), 'Hello, world!' )
		asrt( str_short('Hello', 13), 'Hello' )
		asrt( str_short('Hello,  world! ', 12), 'Hello, wo...' )
		asrt( str_short('Hello\nworld! ', 12), 'Hello world!' )
		asrt( str_short('Hello\nworld! ', 11), 'Hello wo...' )
		asrt( bmark(str_short, ('Hello,  world! ', 5)), 5_000)

	'''

	if width == 0: width = _TERMINAL_WIDTH
	new_text = ' '.join(
		str(text).translate({ord(c): ' ' for c in whitespace}).split()
	)
	if len(new_text) <= width: return new_text
	return new_text[:(width - len(placeholder))] + placeholder

def path_short(fullpath, max_len:int=0)->str:
	r'''
	Shortens a long file name to display.

		path = r'c:\Windows\System32\msiexec.exe'
		asrt(path_short(path, 22), 'c:\Windo...msiexec.exe')
		asrt(path_short(path, 23), 'c:\Window...msiexec.exe')
		asrt(path_short(path), path)

	'''
	if not max_len: max_len = _TERMINAL_WIDTH
	if len(fp := fullpath) <= max_len: return fullpath
	return ''.join(( fp[:( -(-max_len // 2 ) )-3], '...', fp[-(max_len//2):] ))

def _str_unicode_white(categories:tuple=('Zs', 'Zl', 'Zp', 'Cc')):
	' Generate Unicode whitespace list '
	whitespace_chars = []
	for code_point in range(0x110000):
		char = chr(code_point)
		if unicodedata.category(char) in categories:
			whitespace_chars.append(char)
	return whitespace_chars

_UNI_WHITE_ALL:list = []
_UNI_WHITE_ALL_DICT:dict = {}
def str_remove_white(text:str, algo:str='basic', sep:str=' ')->str:
	r'''
	Removes extra whitespace characters.  
	*algo* - 'basic', 'space', 'unicode' where  
		
		- *basic* - remove standard whitespace characters
		- *space* - same as *basic* but preserve new lines.
		- *unicoce* - remove all whitespace characters.


		asrt( str_remove_white(' ba  sic '), 'ba sic')
		asrt( str_remove_white(' spa\n\tce ', 'space'), 'spa\nce')
		asrt( str_remove_white(' no spa\n\tce ', sep=''), 'nospace')

		text = random_str() + '\n' + random_str()
		asrt( bmark(str_remove_white, (text, 'basic',)), 2_000 )
		asrt( bmark(str_remove_white, (text, 'space',)), 2_500 )
		asrt( bmark(str_remove_white, (text, 'unicode',)), 3_000 )

	'''
	global _UNI_WHITE_ALL, _UNI_WHITE_ALL_DICT
	match algo:
		case 'basic':
			return sep.join(text.split())
		case 'space':
			new_line = '\r\n' if '\r\n' in text else '\n'
			lines = text.splitlines()
			cleaned_lines = []
			for line in lines:
				if not line: continue
				cleaned_line = sep.join(line.split())
				cleaned_lines.append(cleaned_line)
			return new_line.join(cleaned_lines)
		case 'unicode':
			if not _UNI_WHITE_ALL:
				_UNI_WHITE_ALL = _str_unicode_white()
				_UNI_WHITE_ALL_DICT = {ord(c): ' ' for c in _UNI_WHITE_ALL}
			tmp = text.translate(_UNI_WHITE_ALL_DICT)
			return sep.join(tmp.split())
		case _:
			raise Exception('Unknown *algo*')

_STR_TO_FLOAT_RE = re.compile(r'(?!^-)[^0-9.]')
def str_to_float(s:str)->float:
	r'''
	Parse a float from a string that may contain currency symbols,
	spaces, commas, etc. Raises ValueError on bad input.

	Examples:

		asrt( str_to_float("$ 1 234.56"), 1234.56 )
		asrt( str_to_float("-€2,500.00"), -2500.0 )
		asrt( str_to_float("3.14159"), 3.14159 )

	'''
	s = s.strip()
	cleaned = _STR_TO_FLOAT_RE.sub('', s)
	return float(cleaned)

_STR_TO_INT_RE = re.compile(r'(?!^-)[^\d]')
def str_to_int(s:str)->int:
	r'''
	Parse an integer from a string that may contain currency symbols,
	spaces, commas, etc. Returns `default` if parsing fails.

	Examples:
	
		asrt( str_to_int('$ 1 234'), 1234 )
		asrt( str_to_int('-€2,500'), -2500)
	
	'''
	s = s.strip()
	cleaned = _STR_TO_INT_RE.sub('', s)
	return int(cleaned)

_often_dct:dict[str, datetime.datetime] = {}

def is_often(ident:str, interval:str)->bool:
	r'''
	Is some event happening too often?  
	The purpose is to protect the user from too frequent notifications.
	*ident* - unique identifier of an event.  
	*interval* - interval for measurement, not less than 1 ms.  

		is_often('_', '1 ms')
		asrt( is_often('_', '1 ms'), True)
		time_sleep('1 ms')
		asrt( is_often('_', '1 ms'), False)
		asrt( bmark(is_often, ('_', '1 ms')), 15_000 )
		asrt( bmark(is_often, ('_', 1)), 3500 )

	'''
	global _often_dct
	UNIT:str = 'ms'
	assert ident, 'the ident should not be empty'
	intr = value_to_unit(interval, unit=UNIT)
	if not (prev_time := _often_dct.get(ident)):
		_often_dct[ident] = datetime.datetime.now()
		return False
	diff = time_diff(prev_time, unit=UNIT)
	if diff < intr:
		return True
	else:
		_often_dct[ident] = datetime.datetime.now()
		return False

def is_app_exe()->bool:
	r'''
	Returns True if the application is converted to *exe*.  

		asrt( is_app_exe(), False)
		asrt( bmark(is_app_exe), 2061 )

	'''
	return getattr(sys, 'frozen', False)

def func_arg(func:Callable)->tuple:
	r'''
	Returns a tuple of function arguments.  

		asrt( func_arg(print), ('args', 'sep', 'end', 'file', 'flush') )
		asrt( bmark(func_arg, (print,)), 480_000 )

	'''
	return tuple( inspect.signature(func).parameters.keys() )

def sys_ver()->float:
	r'''
	Windows version as a number.  
	https://learn.microsoft.com/en-us/windows/win32/sysinfo/operating-system-version  

		asrt( bmark(sys_ver), 79_000 )

	'''
	ver = sys.getwindowsversion()
	return ver.major + ver.minor / 10

def clip_set_img(image):
	r'''
	Copies an image in `PIL.Image` format to the clipboard.
	'''
	win32clipboard.OpenClipboard()
	win32clipboard.EmptyClipboard()
	win32clipboard.SetClipboardData(win32clipboard.CF_DIB, image)
	win32clipboard.CloseClipboard()

def is_in_child_process()->bool:
	r'''
	Are we working in a child process?
	'''
	return os.getpid() != _MAIN_PID

def _target_func(func, queue, args, kwargs):
	result = func(*args, **kwargs)
	queue.put(result)

def run_in_process(func):
	r'''
	Run function in a child process and get result. Blocking call.  
	Caveats:
	
	- Everything must be pickle-friendly
	- There will be an error when using *app_* functions.
	- The function will not see changes in global variables (*gdic*).  

	New process start ~ 3 seconds:

		def _rip_test():
			return 'done'

		def test_run_in_process():
			bmark( run_in_process(_rip_test) )

	'''
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		queue = multiprocessing.Queue()
		p = multiprocessing.Process(target=_target_func
		, args=(func, queue, args, kwargs))
		p.start()
		p.join()

		return queue.get()

	return wrapper

def size_int(size:str|tuple, dst_unit:str='b')->int:
	r'''
	Converts a string with size to an number of the desired unit of measure.  
	*size* - tuple of value and unit or a string with space separated
	value and unit like '2 mb'  

		asrt( size_int((1, 'mb')), 1048576 )
		asrt( size_int('2 mb'), 2097152 )
		asrt( size_int('2 mb', 'kb'), 2048 )
		asrt( size_int('1.5 mb', 'kb'), 1536 )
		asrt( size_int('3 kb', 'MB'), 0 )
		asrt( bmark(size_int, ('3 mb', 'kb')), 1_900 )
		asrt( bmark(size_int, ('1024.5 GB', 'MB')), 1_900 )

	'''
	if isinstance(size, (tuple, list)):
		value, src_unit = size
	else:
		value, src_unit = size.split()
	src_coef = _SIZE_UNITS[src_unit.lower()]
	dst_coef = _SIZE_UNITS[dst_unit.lower()]
	return int(float(value) * src_coef / dst_coef)

def _init():
	if __builtins__.get('gdic', None) != None: return
	__builtins__['gdic'] = {}
	if not is_con(): return
	app:wx.App = wx.App()
	setattr(app, 'que_print', TQueue(consumer=print))
	setattr(app, 'que_log', TQueue(consumer=lambda t: None) )
	setattr(app, 'dir', os.getcwd())
	setattr(app, 'app_threads', {})
	setattr(app, 'app_pid', _GetCurrentProcessId())
	setattr(app, 'cmd_args', argparse.Namespace(dev=True))
	setattr(app, 'tasks', {})
	__builtins__['app'] = app
	
if __name__ != '__main__':
	patch_import()
	_init()
