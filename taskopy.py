import time
import sys
import os
import importlib
import traceback
import threading
import inspect
import types
import configparser
import wx.adv
import wx
import schedule
import keyboard
import win32api
import win32gui
import win32con
import win32file
import win32evtlog
import uptime
from plugins.constants import *
from plugins.tools import *
from plugins.plugin_filesystem import *
from plugins.plugin_system import *
from plugins.plugin_process import *
from plugins.plugin_http_server import http_server_start
from plugins.plugin_hotkey import GlobalHotKeys
from resources.languages import Language

# Docs:
# https://docs.python.org/3/library/threading.html
# https://github.com/boppreh/keyboard
# https://schedule.readthedocs.io/en/stable/
APP_SETTINGS = (
	('dev', False)
	, ('language', 'en')
	, ('menu_hotkey', None)
	, ('editor', 'notepad.exe')
	, ('server_ip', '127.0.0.1')
	, ('server_port', 8275)
	, ('white_list', '127.0.0.1')
	, ('server_silent', True)
	, ('hide_console', False)
	, ('kiosk', False)
	, ('kiosk_key', 'shift')
	, ('log_file_name', tcon.DATE_STR_FILE_SHORT)
)
TASK_OPTIONS = (
	('task_name', None)
	, ('task', True)
	, ('menu', True)
	, ('hotkey', None)
	, ('hotkey_suppress', True)
	, ('schedule', None)
	, ('active', True)
	, ('startup', False)
	, ('sys_startup', False)
	, ('left_click', False)
	, ('log', True)
	, ('single', True)
	, ('running', False)
	, ('submenu', None)
	, ('result', False)
	, ('http', False)
	, ('timeout', 60)
	, ('http_dir', None)
	, ('http_white_list', None)
	, ('err_threshold', 0)
	, ('err_counter', False)
	, ('no_print', False)
	, ('idle', None)
	, ('on_load', False)
	, ('rule', None)
	, ('thread', None)
	, ('last_start', None)
	, ('date', None)
	, ('event_log', None)
	, ('event_xpath', '*')
	, ('on_exit', False)
	, ('hyperactive', False)
	, ('on_file_change', None)
	, ('on_dir_change', None)
	, (
		'on_dir_change_flags'
		, tcon.FILE_NOTIFY_CHANGE_LAST_WRITE
			| tcon.FILE_NOTIFY_CHANGE_FILE_NAME
	)
	, ('on_file_change_flags', tcon.FILE_NOTIFY_CHANGE_LAST_WRITE)
	, ('every', ())
)
_WEEKDAY_HUMAN = {
	'day': 'day'
	, 'sun': 'sunday'
	, 'sunday': 'sunday'
	, 'mon': 'monday'
	, 'monday': 'monday'
	, 'tue': 'tuesday'
	, 'tuesday': 'tuesday'
	, 'wed': 'wednesday'
	, 'wednesday': 'wednesday'
	, 'thu': 'thursday'
	, 'thursday': 'thursday'
	, 'fri': 'friday'
	, 'friday': 'friday'
	, 'sat': 'saturday'
	, 'saturday': 'saturday'
}
_TIME_UNIT_HUMAN = {
	's': 'seconds'
	, 'sec': 'seconds'
	, 'second': 'seconds'
	, 'seconds': 'seconds'
	, 'm': 'minutes'
	, 'min': 'minutes'
	, 'minute': 'minutes'
	, 'minutes': 'minutes'
	, 'h': 'hours'
	, 'hr': 'hours'
	, 'hour': 'hours'
	, 'hours': 'hours'
}
_EVERY_PATTERNS = {
	re.compile(rf'^(\d+)\s*({"|".join(_TIME_UNIT_HUMAN)})$'): 'time_int'
	, re.compile(rf'^(\d+)\s*(to)\s*(\d+)\s*({"|".join(_TIME_UNIT_HUMAN)})$'): 'time_int_rnd'
	, re.compile(rf'^({"|".join(_WEEKDAY_HUMAN)})\s+(\d{{2}}:\d{{2}})$'): 'day'
	, re.compile(r'^(m|min|minute|h|hr|hour)\s*(\:\d+)$'): 'time_day'
}

set_title = win32api.SetConsoleTitle
tasks = None
crontab:types.ModuleType = None
sett = None
lang:Language = None
if getattr(sys, 'frozen', False):
	APP_PATH = os.path.dirname(sys.executable)
	os.chdir(APP_PATH)
	sys.path.append(APP_PATH)
else:
	APP_PATH = os.getcwd()

APP_ICON = r'resources\icon.png'
APP_ICON_DIS = r'resources\icon_dis.png'
PLUGIN_SOURCE = 'plugins\\*.py'
class OVERLAPPED(ctypes.Structure):
	_fields_ = [
		('Internal', ctypes.wintypes.LPVOID),
		('InternalHigh', ctypes.wintypes.LPVOID),
		('Offset', ctypes.wintypes.DWORD),
		('OffsetHigh', ctypes.wintypes.DWORD),
		('Pointer', ctypes.wintypes.LPVOID),
		('hEvent', ctypes.wintypes.HANDLE),
	]

def _errcheck_bool(value, func, args):
	if not value:
		raise ctypes.WinError()
	return args

CancelIoEx = ctypes.windll.kernel32.CancelIoEx
CancelIoEx.restype = ctypes.wintypes.BOOL
CancelIoEx.errcheck = _errcheck_bool
CancelIoEx.argtypes = (
	ctypes.wintypes.HANDLE,  # hObject
	ctypes.POINTER(OVERLAPPED)  # lpOverlapped
)

def _close_directory_handle(handle):
	try:
		CancelIoEx(handle, None)
	except WindowsError as e:
		pass
	except Exception as e:
		tprint(f'unexpected error: {e}')

class Settings:
	''' Load global settings from settings.ini
		Settings from all sections are collected.
	'''
	def __init__(self):
		config = configparser.ConfigParser()
		config.optionxform = str
		try:
			with open(r'settings.ini', 'tr', encoding='utf-8-sig') as f:
				config.read_file(f)
		except FileNotFoundError:
			dev_print('create new settings.ini')
			create_default_ini_file()
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
		for sett in APP_SETTINGS:
			self.__dict__.setdefault(sett[0], sett[1])

def load_crontab(event=None)->bool:
	global tasks
	global crontab
	con_log(f'{lang.load_crontab} {os.getcwd()}')
	try:
		run_bef_reload = []
		if sys.modules.get('crontab') is None:
			crontab = importlib.import_module('crontab')
		else:
			prev_crontab = sys.modules.pop('crontab')
			for attempt in range(100):
				try:
					tmp_crontab = importlib.import_module('crontab')
					break
				except PermissionError:
					dev_print(f'permission error {attempt=}')
					time.sleep(.01)
				except:
					sys.modules['crontab'] = prev_crontab
					trace_full, trace_short = _exc_texts()
					con_log(lang.warn_crontab_reload + str_indent(trace_full))
					warning(
						f'{lang.warn_crontab_reload}\n\n{trace_short}'
						, title=lang.menu_reload
					)
					return False
			else:
				raise Exception('No more attempts to reload crontab')
			for task in tasks.task_dict.values():
				if not task.get('thread'): continue
				run_bef_reload.append(task)
			tasks.close()
			del tmp_crontab
			del prev_crontab
			del sys.modules['crontab']
			del crontab
			crontab = importlib.import_module('crontab')
		load_modules()
		tasks = Tasks()
		app.tasks = tasks
		for rtask in run_bef_reload:
			dev_print('still running:', rtask['task_func_name'])
			if not (task := tasks.task_dict.get(rtask['task_func_name']) ):
				continue
			task['thread'] = rtask['thread']
			task['last_start'] = rtask['last_start']
			task['running'] = rtask['running']
		tasks.run_at_crontab_load()
		tasks.enabled = app.enabled
		return True
	except:
		trace_full, trace_short = _exc_texts()
		con_log(
			lang.warn_crontab_reload
			, str_indent(trace_full)
		)
		warning(
			f'{lang.warn_crontab_reload}\n\n{trace_short}'
			, title=lang.menu_reload
		)
		return False
	
def load_modules():
	'''
	(Re)Loads all application plugins and
	crontab extensions if any.
	'''
	global crontab
	if not hasattr(sett, 'own_modules'):
		sett.own_modules = {'plugins.constants'}
		for obj_name, obj in crontab.__dict__.items():
			if not (
				hasattr(obj, '__module__')
				and obj.__module__ != 'crontab'
				and not obj.__module__.startswith('pyimod')
				and hasattr(sys.modules[obj.__module__], '__file__')
			): continue
			try:
				if os.path.relpath(
					inspect.getfile(sys.modules[obj.__module__])
				).startswith('.'):
					continue
				sett.own_modules.add(obj.__module__)
			except ValueError:
				continue
	for mdl_name in sett.own_modules:
		prev_mdl = sys.modules.pop(mdl_name)
		try:
			tmp_mdl = importlib.import_module(mdl_name)
		except PermissionError:
			con_log(f'permission error: {mdl_name}')
		except ModuleNotFoundError:
			if traceback.format_exc().rstrip().endswith("_patch'"):
				con_log(f'patch removed: {mdl_name}')
			else:
				raise
		except:
			sys.modules[mdl_name] = prev_mdl
			trace_full, trace_short = _exc_texts()
			con_log(
				lang.warn_mod_reload.format(mdl_name)
				+ str_indent(trace_full)
			)
			warning(
				'{}:\n\n{}'.format(
					lang.warn_mod_reload.format(mdl_name)
					, trace_short
				)
				, title=lang.menu_reload
			)
			continue
		del tmp_mdl
		del prev_mdl
		del sys.modules[mdl_name]
		mdl = importlib.import_module(mdl_name)
		for obj_name, obj in mdl.__dict__.items():
			if (
				obj_name.startswith('_')
				or ( isinstance(object, types.ModuleType) )
				or (mdl_name != getattr(obj, '__module__', mdl_name) )
			):
				continue
			if not isinstance(obj, types.FunctionType):
				setattr(crontab, obj_name, obj)
				continue
			for mdl_name_2 in sett.own_modules:
				if hasattr(sys.modules[mdl_name_2], obj_name):
					setattr(sys.modules[mdl_name_2]
						, obj_name, decor_except_status(obj))
			if hasattr(crontab, obj_name):
				setattr(crontab, obj_name, decor_except_status(obj))
		sys.modules[mdl_name] = mdl

class SuppressPrint:
	def __enter__(self):
		self._original_stdout = sys.stdout
		sys.stdout = open(os.devnull, 'w')

	def __exit__(self, exc_type, exc_val, exc_tb):
		sys.stdout.close()
		sys.stdout = self._original_stdout

class Task:

	def __init__(self):
		self.name:str = ''
		self.every:Union[str, tuple] = ''
		self.func = None
		self.menu:bool = True
		self.submenu:str = ''

class Tasks:
	''' Tasks from the crontab and their properties '''
	REGEX_DATE = re.compile(r'^(\d\d\d\d|\*)\.(\d\d|\*)\.(\d\d|\*)\s+(\d\d|\*)\:(\d\d|\*)$')

	def __init__(self):
		self.enabled = True
		self.task_dict = {}
		self.task_list_menu = []
		self.task_list_submenus = []
		self.task_list_startup = []
		self.task_list_left_click = []
		self.task_list_sys_startup = []
		self.task_list_http = []
		self.task_list_idle = []
		self.task_list_crontab_load = []
		self.task_list_exit = []
		self.dir_change_stop = []
		self.event_handlers = []
		self.idle_min = 0
		self.http_server = None
		self.global_hk = None
		self.global_hk_thread_id = None
		for item in dir(crontab):
			if item.startswith('_'): continue
			task_obj = getattr(crontab, item)
			if not isinstance(task_obj, types.FunctionType): continue
			if task_obj.__module__ != 'crontab': continue
			
			task_opts = {}
			params = inspect.signature(task_obj).parameters
			for opt, opt_def in TASK_OPTIONS:
				param = params.get(opt)
				if param == None:
					task_opts[opt] = opt_def
				else:
					task_opts[opt] = param.default
			if not task_opts['task']: continue
			if not task_opts['active']: continue
			task_opts['task_func'] = task_obj
			task_opts['task_func_name'] = item
			if task_opts['task_name']:
				task_opts['task_name_full'] = f'{item} ({task_opts["task_name"]})'
			else:
				task_opts['task_name'] = func_name_human(item)
				task_opts['task_name_full'] = task_opts['task_name']
			if task_opts['schedule']: self.add_schedule(task_opts)
			if task_opts['every']: self.add_every(task_opts)
			if task_opts['date']: self.add_schedule_date(task_opts)
			if task_opts['hotkey']: self.add_hotkey(task_opts)
			if task_opts['left_click']:
				self.task_list_left_click.append(task_opts)
				app.taskbaricon.Bind(
					wx.adv.EVT_TASKBAR_LEFT_DOWN
					, lambda evt, temp=task_opts:
						self.run_task(task=temp, caller=CALLER_LEFT_CLICK)
				)
			if task_opts['startup']:
				self.task_list_startup.append(task_opts)
			if task_opts['sys_startup']:
				self.task_list_sys_startup.append(task_opts)
			if task_opts['on_load']:
				self.task_list_crontab_load.append(task_opts)
			if task_opts['on_exit']:
				self.task_list_exit.append(task_opts)
			if task_opts['on_file_change']:
				self.add_dir_change_watch(task_opts, is_file=True
				, path=task_opts['on_file_change'])
			if task_opts['on_dir_change']:
				self.add_dir_change_watch(task_opts, is_file=False
				, path=task_opts['on_dir_change'])
			self.task_dict[ task_opts['task_func_name'] ] = task_opts
			if task_opts['menu']:
				submenu = None
				if '__' in task_opts['task_func_name']:
					submenu, sm_name = task_opts['task_func_name'].split('__', maxsplit=1)
					submenu = submenu.replace('_', ' ')
					sm_name = sm_name.replace('_', ' ')
					if not sm_name[0].isupper(): sm_name = sm_name.capitalize()
					task_opts['task_name_submenu'] = sm_name
				if s := task_opts.get('submenu'): submenu = s
				if submenu:
					if not submenu[0].isupper(): submenu = submenu.capitalize()
					for m in self.task_list_submenus:
						if m[0] == submenu:
							m[1].append(task_opts)
							break
					else:
						self.task_list_submenus.append(
							(submenu, [task_opts])
						)
				else:
					self.task_list_menu.append(task_opts)
			if task_opts['http']:
				if not task_opts['http_dir']:
					task_opts['http_dir'] = temp_dir()
				self.task_list_http.append(task_opts)
				if (wl := task_opts['http_white_list']):
					if isinstance(wl, str):
						task_opts['http_white_list'] = []
						for ip in wl.split(','):
							task_opts['http_white_list'].append(ip.strip())
			if task_opts['idle']: self.add_idle_task(task_opts)
			if task_opts['event_log']: self.add_event_handler(task_opts)
			if task_opts['rule'] and not is_iter(task_opts['rule']):
				task_opts['rule'] = (task_opts['rule'], )
		self.task_list_menu.sort( key=lambda k: k['task_name'].lower() )
		self.task_list_submenus.sort( key=lambda k: k[0].lower() )
		for subm in self.task_list_submenus:
			subm[1].sort( key=lambda k: k['task_name'].lower() )
		left_click_tasks_count = len(self.task_list_left_click)
		if left_click_tasks_count > 1:
			warning(
				lang.warn_left_click.format(
					', '.join(tuple(
						t['task_name'] for t in self.task_list_left_click
					))
				)
			)
		elif left_click_tasks_count == 0:
			app.taskbaricon.Bind(
				wx.adv.EVT_TASKBAR_LEFT_DOWN
				, app.taskbaricon.on_left_down
			)
		if self.global_hk:
			self.global_hk_thread_id = thread_start(
				self.global_hk.listen, err_msg=True)
		if self.task_list_http:
			thread_start(http_server_start, args=(self,), err_msg=True)
		self.sched_thread_id = thread_start(self.run_scheduler, err_msg=True)
		dev_print(f'Total number of tasks: {len(self.task_dict)}')
	
	def add_hotkey(self, task):
		
		def hk_error(error):
			con_log(error)
			warning(
				lang.warn_hotkey.format(
					task['task_name_full']
				)
				+ ':\n' + task['hotkey']
			)
			
		if task['hotkey_suppress']:
			try:
				if not self.global_hk:
					self.global_hk = GlobalHotKeys()
				self.global_hk.register(
					task['hotkey']
					, func=self.run_task
					, func_args=[task, 'hotkey']
				)
			except Exception as e:
				hk_error(repr(e))
		else:
			try:
				keyboard.add_hotkey(
					hotkey=str(task['hotkey']).lower()
					, callback=self.run_task
					, suppress=False
					, args=[task, 'hotkey']
				)
			except Exception as e:
				hk_error(repr(e))

	def add_dir_change_watch(self, task:dict, path:str, is_file:bool):
		' Watch for changes in directory '
		WAIT_SEC = .1
		FILE_LIST_DIRECTORY = 0x0001
		BUFFER_LENGTH = 1024

		def dir_watch(task:dict, path:str, is_file:bool=False):
			while True:
				try:
					hDir = win32file.CreateFile (
						file_dir(path) if is_file else path
						, FILE_LIST_DIRECTORY
						, win32con.FILE_SHARE_READ
							| win32con.FILE_SHARE_WRITE
							| win32con.FILE_SHARE_DELETE
						, None
						, win32con.OPEN_EXISTING
						, win32con.FILE_FLAG_BACKUP_SEMANTICS
						, None
					)
					self.dir_change_stop.append(hDir)
					filename = file_name(path)
					prev_file = ('', time.time())
					if is_file:
						flags = task['on_file_change_flags']
					else:
						flags = task['on_dir_change_flags']
					results = win32file.ReadDirectoryChangesW(
						hDir,
						BUFFER_LENGTH,
						not is_file,
						flags,
						None,
						None
					)
				except pywintypes.error as e:
					if e.winerror == 995:
						return
					elif e.winerror in (6, 53, 64):
						dev_print(f'disconnected ({e.winerror}) from {path}')
						if e.winerror != 53:
							try:
								_close_directory_handle(hDir)
							except Exception as e2:
								dev_print(f'_close_directory_handle exception: {e2}')
						try:
							self.dir_change_stop.remove(hDir)
							del hDir
						except Exception as e:
							dev_print(f'hDir not exists ({e})')
						time.sleep(13.0)
						continue
					else:
						tprint(f'pywintypes error: {e.args}')
						raise e
				if prev_file[0]:
					pfile, ptime = prev_file
					try:
						cfile, ctime = results[-1][1], time.time()
					except:
						if is_dev():
							print(f'{prev_file=}, {results=}, exception:\n{exc_text()}\n')
							dialog(
								f'Exception in "dir_watch":\n\n{exc_text()}'
								, timeout='5 min'
							)
					if cfile == pfile \
					and ( (ctime - ptime) < WAIT_SEC ):
						prev_file = (cfile, ctime)
						continue
				prev_file = (results[-1][1], time.time())
				for res_action, res_relname in results[:1]:
					if is_file and (
						res_relname != filename
						or res_action != 3
					):
						continue
					if is_file:
						fullpath = path
					else:
						fullpath = os.path.join(path, res_relname)
					self.run_task(
						task=task
						, caller=CALLER_FILE_CHANGE if is_file else CALLER_DIR_CHANGE
						, data=(
							fullpath
							, FILE_ACTIONS.get(res_action, 'unknown')
						)
					)
		thread_start(
			dir_watch
			, kwargs={
					'task': task
					, 'path': path
					, 'is_file': is_file
			}
			, err_msg=True
		)

	def add_every(self, task:dict):

		def exc_rep(e):
			con_log(repr(e))
			warning(
				lang.warn_schedule.format(task['task_name_full'])
			)
			
		status, data = every_parse(task['every'])
		if not status:
			warning(lang.warn_every.format(
				task['task_name'], task['every']
			))
			return
		for ev_type, ev_items in data:
			if ev_type == 'time_int':
				sched_unit = _TIME_UNIT_HUMAN[ev_items[1]]
				try:
					sched = schedule.every( int(ev_items[0]) )
					getattr(sched, sched_unit).do(
						self.run_task
						, task=task
						, caller=CALLER_SCHEDULER
					)
				except Exception as e:
					exc_rep(e)
			elif ev_type == 'time_int_rnd':
				sched_unit = _TIME_UNIT_HUMAN[ev_items[3]]
				try:
					sched = schedule.every(
						int(ev_items[0])
					).to( int(ev_items[2]) )
					getattr(sched, sched_unit).do(
						self.run_task
						, task=task
						, caller=CALLER_SCHEDULER
					)
				except Exception as e:
					exc_rep(e)
			elif ev_type == 'day':
				sched_unit = _WEEKDAY_HUMAN[ev_items[0]]
				try:
					sched = schedule.every()
					getattr(sched, sched_unit).at(ev_items[1]).do(
						self.run_task
						, task=task
						, caller=CALLER_SCHEDULER
					)
				except Exception as e:
					exc_rep(e)
			elif ev_type == 'time_day':
				sched_unit = 'hour' if ev_items[0].startswith('h') else 'minute'
				try:
					sched = schedule.every()
					getattr(sched, sched_unit).at(ev_items[1]).do(
						self.run_task
						, task=task
						, caller=CALLER_SCHEDULER
					)
				except Exception as e:
					exc_rep(e)
			else:
				warning(
					lang.warn_schedule.format(task['task_name_full'])
				)

	def add_schedule(self, task):
		'''
		*task* - a dict with task options.  
		'''
		intervals = task['schedule']
		if isinstance(intervals, str): intervals = (intervals,)
		for inter in intervals:
			try:
				sched_rule = (
					'schedule.' + inter
					+ f'.do(self.run_task, task=task, caller="{CALLER_SCHEDULER}")'
				)
				eval(sched_rule)
			except Exception as e:
				con_log(repr(e))
				warning(
					lang.warn_schedule.format(task['task_name_full'])
					+ ':\n' + inter
				)

	def add_schedule_date(self, task):
		''' task - dict with task options '''
		
		def run_task_date(date_dic:dict, task:dict):
			dt_now = datetime.datetime.now().replace(second=0, microsecond=0)
			if dt_now != date_fill(date_dic):
				return
			self.run_task(task=task, caller=CALLER_SCHEDULER)
		DATE_PARTS = ('year', 'month', 'day', 'hour', 'minute')
		dates = task['date']
		if isinstance(dates, str): dates = [dates]
		for date in dates:
			if not (matches := self.REGEX_DATE.findall(date)):
				warning(
					lang.warn_date_format.format(
						task['task_name_full']
						, date
					)
				)
				continue
			dt_dic = {}
			for num, part in enumerate(matches[0]):
				dt_dic[ DATE_PARTS[num] ] = None if part == '*' else int(part)
			schedule.every().minute.do(
				run_task_date, date_dic=dt_dic, task=task)

	def run_at_startup(self):
		if sett.hide_console:
			win_hide(app.app_hwnd)
		for task in self.task_list_startup:
			self.run_task(task, caller=CALLER_STARTUP)
			
	def run_at_sys_startup(self):
		if uptime.uptime() < 120:
			for task in self.task_list_sys_startup:
				self.run_task(task, caller=CALLER_SYS_STARTUP)
	
	def run_at_crontab_load(self):
		for task in self.task_list_crontab_load:
			self.run_task(task, caller=CALLER_LOAD)
	
	def task_opt_set(self, task_func_name:str, option:str, value):
		''' Sets the option for the task
		'''
		if not (task := self.task_dict.get(task_func_name)):
			dev_print(f'task not found: {task_func_name}, option: {option}')
			return
		task[option] = value

	def task_opt_get(self, task_func_name:str, option:str):
		''' Gets the option for the task
		'''
		if not (task := self.task_dict.get(task_func_name)):
			dev_print(f'task not found: {task_func_name}, option: {option}')
			return
		return task.get(option, 'task_opt_get error: option not found')

	def run_task(self, task:dict, caller:str=None, data=None
	, result:list=None, wait_event:threading.Event=None):
		'''
		Logging, threading, error catching and other stuff.
		task - dict with task options
		caller - who actually launched the task.
			It can be 'hotkey', 'menu', 'scheduler', 'http' etc.,
			so you can find out inside the task function who
			started function this time.
		data - pass some data to task
		result - list in which we will place result of task. It is
			passed through all inner fuctions (run_task_inner and
			catcher).
		'''
		def run_task_inner(result:list=None):
			def catcher(result:list=None):
				try:
					self.task_opt_set(task['task_func_name']
						, 'running', True)
					self.task_opt_set(task['task_func_name']
						, 'thread', threading.current_thread().name)
					task_kwargs = {}
					func_args = set(
						k.lower()
						for k in inspect.signature(
							task['task_func']
						).parameters.keys()
					)
					if 'caller' in func_args:
						task_kwargs['caller'] = caller
					if 'data' in func_args:
						task_kwargs['data'] = data
					task['last_start'] = datetime.datetime.now()
					if task['no_print']:
						with SuppressPrint():
							r = task['task_func'](**task_kwargs)
					else:
						r = task['task_func'](**task_kwargs)
					if result != None: result.append(r)
					try:
						if ( t := tasks.task_dict.get(task['task_func_name'], {}) ):
							t['running'] = False
							t['thread'] = None
					except NameError:
						dev_print(f'"tasks" not exists for the task {task["task_func_name"]}')
					self.task_opt_set(task['task_func_name']
						, 'err_counter', 0)
					if wait_event: wait_event.set()
				except Exception:
					try:
						if ( t := tasks.task_dict.get(task['task_func_name'], {}) ):
							t['running'] = False
							t['thread'] = None
					except NameError:
						dev_print('task stopped after reload: '
						+ task['task_func_name'])
					err_counter = self.task_opt_get(
						task['task_func_name']
						, 'err_counter'
					) + 1
					trace_full, trace_short = _exc_texts()
					con_log(
						lang.warn_task_error.format(task['task_name_full'])
						+ str_indent(trace_full)
					)
					if not result is None:
						result.append('task error')
					if err_counter > self.task_opt_get(
						task['task_func_name']
						, 'err_threshold'
					):
						dev_print(f'err_counter={err_counter}')
						self.task_opt_set(task['task_func_name']
							, 'err_counter', 0)
						warning(
							lang.warn_task_error.format(task['task_name_full'])
							+ f'\n\n{trace_short}'
						)
					else:
						self.task_opt_set(task['task_func_name']
							, 'err_counter', err_counter)
			if (
				(not self.enabled)
				and ( not task['hyperactive'])
				and caller != tcon.CALLER_MENU
			): return
			if task['single'] and task['running']: return
			if task['rule']:
				for rule in task['rule']:
					try:
						if not rule(): return
					except Exception as e:
						con_log(f'{task["task_name"]} rule exception: {e}')
						warning(lang.warn_rule_exc.format(task["task_name"], e))
						return
			if task['log']:
				cs = f' ({caller})' if caller else ''
				con_log(f'task{cs}: {task["task_name_full"]}')
			if task['result']:
				thr = threading.Thread(target=catcher, args=(result,)
				, daemon=daemon)
				thr.start()
				thr.join()
				app.app_threads[thr.ident] = {
					'func': 'catcher: ' + task['task_name']
					, 'stime': time_now()
					, 'thread': thr
				}
			else:
				thr = threading.Thread(target=catcher, daemon=daemon)
				thr.start()
				app.app_threads[thr.ident] = {
					'func': 'catcher: ' + task['task_name']
					, 'stime': time_now()
					, 'thread': thr
				}
		daemon = (caller != CALLER_EXIT)
		if task['result'] and not result is None:
			thread_start(run_task_inner, thr_daemon=daemon, args=(result,)
				, err_msg=True)
		else:
			run_task_inner()

	def add_idle_task(self, task):
		dur = value_to_unit(task['idle'], 'ms')
		task['idle_dur'] = int(dur)
		task['idle_done'] = False
		self.task_list_idle.append(task)
	
	def add_event_handler(self, task):

		def run_task_with_data(reason, context, event):
			' Converts event XML to dictionary '
			r'''
			<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
				<System>
					<Provider Name="Microsoft-Windows-DistributedCOM" Guid="{1B562E86-B7AA-4131-BADC-B6F3A001407E}" EventSourceName="DCOM" /> 
					<EventID Qualifiers="0">10010</EventID> 
					<Version>0</Version> 
					<Level>2</Level> 
					<Task>0</Task> 
					<Opcode>0</Opcode> 
					<Keywords>0x8080000000000000</Keywords> 
					<TimeCreated SystemTime="2021-02-10T12:24:20.581005200Z" /> 
					<EventRecordID>729301</EventRecordID> 
					<Correlation /> 
					<Execution ProcessID="952" ThreadID="41804" /> 
					<Channel>System</Channel> 
					<Computer>DB</Computer> 
					<Security UserID="S-1-5-20" /> 
				</System>
				<EventData>
					<Data Name="param1">{AAC1009F-AB33-48F9-9A21-7F5B88426A2E}</Data> 
				</EventData>
			</Event>
			'''
			xml_str = win32evtlog.EvtRender(
				event, win32evtlog.EvtRenderEventXml )
			self.run_task(
				task=task
				, caller=CALLER_EVENT
				, data=DataEvent(xml_str)
			)

		try:
			self.event_handlers.append(
				win32evtlog.EvtSubscribe(
					task['event_log']
					, win32evtlog.EvtSubscribeToFutureEvents
					, None
					, run_task_with_data
					, None
					, task['event_xpath']
					, None
					, None
				)
			)
		except:
			warning(
				lang.warn_event_format.format( task['task_name_full'] )
			)

	def run_scheduler(self):
		time.sleep(0.01)
		local_id = tasks.sched_thread_id
		afk = True
		if self.task_list_idle:
			afk = False
			self.idle_min = min((t['idle_dur'] for t in self.task_list_idle))
		cur_thread_id = local_id
		while (cur_thread_id == local_id):
			schedule.run_pending()
			if self.task_list_idle:
				ms = int(uptime.uptime() * 1000) - win32api.GetLastInputInfo()
				if ms < self.idle_min:
					if afk:
						afk = False
						for task in self.task_list_idle:
							task['idle_done'] = False
				else:
					afk = True
					for task in self.task_list_idle:
						if task['idle_done']: continue
						if ms >= task['idle_dur']:
							self.run_task(task, caller=CALLER_IDLE)
							task['idle_done'] = True
			time.sleep(1)
			try:
				cur_thread_id = tasks.sched_thread_id
			except NameError:
				dev_print('tasks not exists')
				break

	def close(self):
		''' Destructor.
			Remove scheduler jobs, hotkey bindings, stop http server
			, close event handlers.
		'''
		if self.http_server:
			self.http_server.shutdown()
			self.http_server.socket.close()
		try:
			keyboard.unhook_all()
		except:
			dev_print('no hotkeys with keyboard module')
		if self.global_hk:
			self.global_hk.unregister()
			self.global_hk.stop_listener()
			self.global_hk = None
		schedule.clear()
		for eh in self.event_handlers:
			try:
				eh.close()
			except Exception as e:
				dev_print(f'event close error: {e}')
		for h in self.dir_change_stop: _close_directory_handle(h.handle)

def create_menu_item(menu, task, func=None, parent_menu=None):
	''' Task - task dict or menu item label
		If task is a dict then func = tasks.run_task
		parent_menu - only for submenu items.
	'''
	if isinstance(task, dict):
		tname = task['task_name']
		if task['hotkey']:
			tname = f"{tname}\t{task['hotkey'].title()}"
		func = lambda evt, temp=task: tasks.run_task(task=temp, caller=CALLER_MENU)
	else:
		tname = task
	if parent_menu:
		tname = task.get('task_name_submenu', tname)
		item = wx.MenuItem(menu, -1, tname)
	else:
		item = wx.MenuItem(menu, -1, tname)
	if parent_menu:
		parent_menu.Bind(wx.EVT_MENU, func, id=item.GetId())
	else:
		menu.Bind(wx.EVT_MENU, func, id=item.GetId())
	menu.Append(item)

class TaskBarIcon(wx.adv.TaskBarIcon):
	def __init__(self, frame):
		self.frame = frame
		self.text_dic = {}
		super(TaskBarIcon, self).__init__()
		self.icon = wx.Icon(APP_ICON)
		self.icon_dis = wx.Icon(APP_ICON_DIS)
		self.set_icon()
		self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

	def CreatePopupMenu(self):
		menu = wx.Menu()
		if not sys.modules.get('crontab') is None:
			if keyboard.is_pressed('shift'):
				for task in tasks.task_dict.values():
					if not task['submenu']: create_menu_item(menu, task)
			else:
				for task in tasks.task_list_menu: create_menu_item(menu, task)
			for subm in tasks.task_list_submenus:
				submenu = wx.Menu()
				for task in subm[1]:
					create_menu_item(submenu, task, parent_menu=menu)
				menu.AppendSubMenu(submenu, subm[0])
		if sett.kiosk and not keyboard.is_pressed(sett.kiosk_key): return menu
		menu.AppendSeparator()
		create_menu_item(menu, lang.menu_edit_crontab, self.on_edit_crontab)
		create_menu_item(menu, lang.menu_reload, load_crontab)
		create_menu_item(menu
			, lang.menu_disable if tasks.enabled else lang.menu_enable
			, self.on_disable
		)
		create_menu_item(menu, lang.menu_list_run_tasks, self.running_tasks)
		if sett.dev:
			create_menu_item(menu, lang.menu_restart, self.on_restart)
			create_menu_item(menu, lang.menu_edit_settings, self.on_edit_settings)
		if sett.dev or keyboard.is_pressed('shift'):
			create_menu_item(menu, lang.menu_command, self.run_command)
		create_menu_item(menu, lang.menu_exit, self.on_exit)
		return menu

	def run_command(self, event=None):
		show_app_window()
		cmd = input(f'{lang.menu_command_con}: ')
		if cmd:	print(eval(cmd))

	def set_icon(self, dis:bool=False, text=APP_FULLNAME
	, del_text_key=None):
		'''
		Change icon text.
		Provide a string to just replace icon text or provide
		a dictionary to update line made of `self.text_dic_key`
		items.
		*del_text_key* - delete the specified key from
		the `self.text_dic_key`
		'''
		if isinstance(text, str):
			icon_text = text
		elif isinstance(text, dict):
			self.text_dic.update(text)
			if del_text_key: self.text_dic.pop(del_text_key, None)
			icon_text = '\n'.join((
				f'{k}{v}' for k, v in self.text_dic.items()
			))
		self.SetIcon(self.icon_dis if dis else self.icon, icon_text)
	

	def on_left_down(self, event=None):
		''' Default action on left click to tray icon
		'''
		if sett.kiosk and not keyboard.is_pressed(sett.kiosk_key): return
		if app.app_hwnd:
			if sett.hide_console:
				if win_is_visible(app.app_hwnd):
					win_hide(app.app_hwnd)
				else:
					show_app_window()
			else:
				show_app_window()

	def on_exit(self, event=None, force:bool=False)->bool:
		'''
		*force* - do not wait for tasks.
		'''
		TASKS_MSG_MAX = 10
		running_tasks = self.running_tasks(show_msg=False)
		if running_tasks:
			tasks_str = '\r\n'.join(
				tuple(
					t['task_name'] for t in running_tasks
				)[:TASKS_MSG_MAX]
			)
			if len(running_tasks) > TASKS_MSG_MAX:
				tasks_str += '\r\n...'
			if not force:
				if dialog(
					lang.warn_runn_tasks_msg.format( len(running_tasks) )
					+ '\r\n\r\n' + tasks_str
					, title=lang.menu_exit
					, buttons=(lang.button_close, lang.button_cancel)
					, return_button=True
				)[1] != lang.button_close:
					return False
		if tasks.task_list_exit:
			tprint(
				lang.warn_on_exit + ': '
				 + ', '.join(
					t['task_name'] for t
					in tasks.task_list_exit
				 )
			)
			for task in tasks.task_list_exit:
				tasks.run_task(task, caller=CALLER_EXIT)
		con_log(lang.menu_exit)
		tasks.close()
		wx.CallAfter(self.Destroy)
		self.frame.Close()
		return True

	def running_tasks(self, show_msg:bool= True
	, event=None)->list:
		'''
		Prints running tasks and shows dialog
		(if show_msg == True).  
		Returns the list of running task names.
		'''
		TASKS_MSG_MAX = 10
		running_tasks = tuple(
			t for t in tasks.task_dict.values() if t['running']
		)
		if is_dev(): app_threads_print()
		if not running_tasks:
			if show_msg:
				dialog(lang.warn_no_run_tasks
					, title=lang.menu_list_run_tasks
					, timeout=3
					, wait=False)
			return []
		cur_threads = []
		for thread in threading.enumerate():
			if thread._target is None: continue
			cur_threads.append(thread.name)
		table = [('Task function', 'Thread'
		, 'Start time', 'Running time')]
		for t in running_tasks:
			if t['thread'] in cur_threads:
				thread = t['thread']
			else:
				thread = str(t['thread']) + ' (nonexistent)'
			last_start = None
			duration = None
			if t['last_start']:
				last_start = t['last_start'].strftime(
					'%Y.%m.%d %H:%M:%S')
				duration = str(
					time_now() - t['last_start']
				).split('.')[0]
			table.append((
				t['task_func_name']
				, thread
				, last_start
				, duration
			))
		if len(table) > 1:
			print(lang.warn_runn_tasks_con + ':')
			table_print(table, use_headers=True)
		if not show_msg: return running_tasks
		tasks_str = '\r\n'.join(
			tuple(t['task_name'] for t in running_tasks)[:TASKS_MSG_MAX]
		)
		if len(running_tasks) > TASKS_MSG_MAX:
			tasks_str += '\r\n...'
		dialog(tasks_str, timeout='10 sec', wait=False)

	def on_edit_crontab(self, event=None):
		proc_start(sett.editor, os.path.join(APP_PATH, 'crontab.py'))

	def on_edit_settings(self, event=None):
		proc_start(sett.editor, os.path.join(APP_PATH, r'settings.ini'))

	def on_disable(self, event=None):
		tasks.enabled = not tasks.enabled
		app.enabled = tasks.enabled
		if tasks.enabled:
			set_title(APP_NAME)
			con_log('Enabled')
		else:
			set_title(f'Disabled {APP_NAME}')
			con_log('Disabled')
		self.set_icon(dis=not tasks.enabled)
	
	def on_restart(self, event=None):
		if not self.on_exit(): return
		dev = ''
		if '--developer' in sys.argv: dev = '--developer'
		if getattr(sys, 'frozen', False):
			file_open(
				os.path.join(APP_PATH, APP_NAME + '.exe')
				, parameters=dev
			)
		else:
			file_open(
				os.path.join(APP_PATH, APP_NAME + '.py')
				, parameters=dev
			)

	def popup_menu_hk(self):
		app.frame.SetFocus()
		time.sleep(0.1)
		app.frame.PopupMenu(self.CreatePopupMenu())

class App(wx.App):

	def OnInit(self):
		self.enabled = True
		self.frame=wx.Frame(None, style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
		self.taskbaricon = TaskBarIcon(self.frame)
		self.app_pid = os.getpid()
		self.app_threads = {}
		hwnd_list = win_find(APP_NAME)
		if len(hwnd_list) == 1:
			self.app_hwnd = hwnd_list[0]
		elif len(hwnd_list) > 1:
			self.app_hwnd = hwnd_list[0]
			if not sett.dev:
				warning(
					lang.warn_too_many_win.format(
					APP_NAME, len(hwnd_list) )
				)
		else:
			self.app_hwnd = 0
			if sett.dev:
				warning(f'None of {APP_NAME} windows was found')
		return True

	def InitLocale(self):
		'''Override with nothing (or impliment local if actually needed)'''
		pass

	def popup_menu_hk(self):
		tprint('app menu by hotkey')
		self.frame.SetFocus()
		time.sleep(0.1)
		self.frame.PopupMenu(self.taskbaricon.CreatePopupMenu())
	
	def exit(self, force:bool=False):
		self.taskbaricon.on_exit(force=force)

def show_app_window():
	try:
		win32gui.ShowWindow(app.app_hwnd, win32con.SW_RESTORE)
		win32gui.SetForegroundWindow(app.app_hwnd)
	except Exception as e:
		dev_print(f'show window exception: {e}')

def every_parse(every:Union[str, list, tuple])->Tuple[bool, list]:
	r'''
	Examples:

		from taskopy import every_parse
		for es in ('5m', '5M', '5 m', '5 min', '5min'
		, '5 minutes', 'mon 05:45', 'Mon 05:45'
		, 'day 17:45', 'hour :30', 'h:30', ('5m', '5s')
		, '5 to 6 min', '5to6min'):
			tass( every_parse(es)[0], True )
		for es in ('5y', '5', '5 mins', '5mins', 5
		, 'mon 5:45', 'hour 0:30', ('5m', 'hour')):
			tass( every_parse(es)[0], False )
		
	'''
	if isinstance(every, str):
		every = (every, )
	elif not is_iter(every):
		return False, []
	result = []
	for ev_str in every:
		ev_str = ev_str.strip().lower()
		for pat, pat_type in _EVERY_PATTERNS.items():
			if (match := pat.findall(ev_str)):
				result.append((pat_type, match[0]))
				break
		else:
			return False, []
	return True, result

def _exc_texts()->tuple:
	' Get full and short text of exception '
	trace_full = traceback.format_exc().strip()
	trace_short = '\n'.join(trace_full.splitlines()[-3:])
	return trace_full, trace_short

def main():
	global app
	global tasks
	global sett
	global lang
	set_title(APP_NAME)
	try:
		sett = Settings()
	except Exception as e:
		print(f'Cannot load settings:\n{repr(e)}')
		warning(f'Cannot load settings:\n{repr(e)}')
		return
	__builtins__.sett = sett
	lang = Language(sett.language)
	__builtins__.lang = lang
	if sett.kiosk:
		sett.dev = False
		sett.hide_console = True
	print(f'{APP_NAME} version {APP_VERSION}')
	print(lang.load_homepage)
	print(lang.load_donate + '\n\n')
	try:
		app = App(False)
		app.load_crontab = load_crontab
		app.show_window = app.taskbaricon.on_left_down
		app.dir = APP_PATH
		__builtins__.app = app
		if load_crontab():
			tasks.run_at_startup()
			tasks.run_at_sys_startup()
			if sett.dev: app.taskbaricon.popup_menu_hk()
		app.MainLoop()
	except Exception as e:
		trace_full, _ = _exc_texts()
		msg = f'General exception:\n\n{trace_full}'
		print('\n', msg)
		warning(msg)
		input('Press Enter to exit...')
	except KeyboardInterrupt:
		tprint('Interrupted by keyboard')
		time.sleep(2)


if __name__ == '__main__': main()
