
import time
import sys
import os
import importlib
import traceback
import threading
import inspect
import types
import wx.adv
import wx
import schedule
import keyboard
import win32api
import win32gui
import win32con
import win32file
import win32evtlog
import gc
import argparse
import msvcrt
from plugins.constants import *
from plugins.tools import *
from plugins.tools import _tlog, _thread_pop
from plugins.plugin_filesystem import *
from plugins.plugin_system import *
from plugins.plugin_system import _idle_millis
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
	, ('http_re', ())
	, ('http_white_list', None)
	, ('err_threshold', 0)
	, ('err_counter', False)
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
		, (
			win32con.FILE_NOTIFY_CHANGE_FILE_NAME
			| win32con.FILE_NOTIFY_CHANGE_DIR_NAME
			| win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES
			| win32con.FILE_NOTIFY_CHANGE_SIZE
			| win32con.FILE_NOTIFY_CHANGE_LAST_WRITE
			| win32con.FILE_NOTIFY_CHANGE_SECURITY
		)
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
crontab:types.ModuleType|None = None
sett:Settings = Settings(ini_file='')
lang:Language = None

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
		self.dir_change_stop = {}
		self.event_handlers:list = []
		self.idle_min:int = 0
		self.http_server = None
		self.global_hk = None
		for task_name in dir(crontab):
			if task_name.startswith('_'): continue
			task_obj = getattr(crontab, task_name)
			if not isinstance(task_obj, types.FunctionType): continue
			if (
				(not getattr(task_obj, TASK_ATTR, False))
				and (task_obj.__module__ != 'crontab')
			): continue
			task_opts:dict = {}
			params = inspect.signature(task_obj).parameters
			for opt, opt_def in TASK_OPTIONS:
				param = params.get(opt)
				if param is None:
					task_opts[opt] = opt_def
				else:
					task_opts[opt] = param.default
			if not task_opts['task']: continue
			if not task_opts['active']: continue
			self.task_dict[task_name] = task_opts
			task_opts['task_func'] = task_obj
			task_opts['task_func_name'] = task_name
			if task_opts['task_name']:
				task_opts['task_name_full'] = f'{task_name} ({task_opts["task_name"]})'
			else:
				task_opts['task_name'] = func_name_human(task_name)
				task_opts['task_name_full'] = task_opts['task_name']
			if task_opts['schedule']: self.add_schedule(task_opts)
			if task_opts['every']: self.add_every(task_opts)
			if task_opts['date']: self.add_schedule_date(task_opts)
			if task_opts['hotkey']: self.add_hotkey(task_opts)
			if task_opts['left_click']:
				if not app.is_cmd_task:
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
			if task_opts['http'] != False:
				if task_opts['http'] == True:
					http_re = (
						''.join(('^', task_opts['task_func_name'], '$')),
					)
				else:
					http_re = task_opts['http']
					if not is_iter(http_re): http_re = (task_opts['http'],)
				task_opts['http_re'] = tuple(re.compile(p) for p in http_re)
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
			if task_opts['rule'] != None:
				if not is_iter(task_opts['rule']):
					task_opts['rule'] = (task_opts['rule'], )
				for rule in task_opts['rule']:
					if not isinstance(rule, Callable):
						msg_warn(lang.warn_rule_type.format(
							task_opts['task_name_full']
						))
		self.task_list_menu.sort( key=lambda k: k['task_name'].lower() )
		self.task_list_submenus.sort( key=lambda k: k[0].lower() )
		for subm in self.task_list_submenus:
			subm[1].sort( key=lambda k: k['task_name'].lower() )
		left_click_tasks_count = len(self.task_list_left_click)
		if left_click_tasks_count > 1:
			msg_warn(
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
			thread_start(self.global_hk.listen
			, err_msg=True, ident='app: global hotkey listener')
		if self.task_list_http and not app.is_cmd_task:
			thread_start(http_server_start, args=(self,), err_msg=True
			, ident='app: http server')
		thread = thread_start(self.run_scheduler, err_msg=True
		, ident='app: scheduler')
		self.sched_thread_id = thread.ident
		if is_dev():
			tprint(f'total number of tasks: {len(self.task_dict)}'
			, tname='app')
	
	def add_hotkey(self, task):
		
		def hk_error(error):
			msg_warn( lang.warn_hotkey.format(
				task['task_name_full'], task['hotkey'], error
			))
			
		if app.is_cmd_task: return
		if task['hotkey_suppress']:
			try:
				if not self.global_hk: self.global_hk = GlobalHotKeys()
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
					hotkey=str(task['hotkey'])
					, callback=self.run_task
					, suppress=False
					, args=(task, 'hotkey')
				)
			except Exception as e:
				hk_error(repr(e))

	def add_dir_change_watch(self, task:dict, path:str, is_file:bool):
		' Watch for changes in directory '
		WAIT_SEC = .1
		FILE_LIST_DIRECTORY = 0x0001
		BUFFER_SIZE = 65536
		RECONNECT_TIMEOUT = 13.0

		def get_dir_handle(dir_path:str)->tuple:
			' Returns (status:bool, handle) or (False, pywintypes.error) '
			try:
				hDir = win32file.CreateFile (
					dir_path
					, FILE_LIST_DIRECTORY
					, (win32con.FILE_SHARE_READ
						| win32con.FILE_SHARE_WRITE
						| win32con.FILE_SHARE_DELETE)
					, None
					, win32con.OPEN_EXISTING
					, win32con.FILE_FLAG_BACKUP_SEMANTICS
					, None
				)
				return True, hDir
			except pywintypes.error as err:
				return False, err
			except Exception as err:
				raise

		def dir_watch(task:dict, path:str, is_file:bool=False):
			dir_path:str = file_dir(path) if is_file else path
			filename = file_name(path)
			prev_file = ('', time.time())
			if is_file:
				flags = task['on_file_change_flags']
			else:
				flags = task['on_dir_change_flags']
			while True:
				status:bool = False
				while not status:
					status, data = get_dir_handle(dir_path)
					if status: break
					if data.winerror == 2:
						msg_warn(lang.warn_path_not_exist.format(path))
						return
					time.sleep(RECONNECT_TIMEOUT)
				hDir = data
				self.dir_change_stop[hDir] = dir_path
				while True:
					if hDir.handle == 0:
						if is_dev():
							tprint('the handle was closed ' + dir_path)
							tlog('the handle was closed ' + dir_path)
						return
					try:
						results = win32file.ReadDirectoryChangesW(
							hDir
							, BUFFER_SIZE
							, not is_file
							, flags
							, None
							, None
						)
					except pywintypes.error as errp:
						if errp.winerror == 995:
							return
						elif errp.winerror in (6, 53, 64):
							self.dir_change_stop.pop(hDir, None)
							try:
								hDir.Close()
							except Exception as err_cl:
								if is_dev():
									dev_print(f'hDir close exception: {err_cl}')
									msg_err(f'hDir close exception: {err_cl}'
									+ f'\n	{hDir.handle=}, {dir_path=}')
							break
						else:
							dev_print(f'pywintypes error: {errp.args}')
							raise errp
					except Exception as errg:
						if is_dev(): con_log(f'general error: {errg}')
						raise errg
					if prev_file[0]:
						pfile, ptime = prev_file
						try:
							cfile, ctime = results[-1][1], time.time()
						except:
							if is_dev():
								msg_err(f'Exception in «dir_watch»'
								, timeout='5 min', source='dir_watch')
						if cfile == pfile and ( (ctime - ptime) < WAIT_SEC ):
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
							, caller=(
								CALLER_FILE_CHANGE if is_file
								else CALLER_DIR_CHANGE
							)
							, data=(
								fullpath
								, FILE_ACTIONS.get(res_action, 'unknown')
							)
						)
					
		if app.is_cmd_task: return
		thread_start(
			dir_watch
			, kwargs={
				'task': task
				, 'path': path
				, 'is_file': is_file
			}
			, err_msg=True
			, ident='app: dir_watch ' + path
		)

	def add_every(self, task:dict):

		def exc_rep(e):
			msg_warn(
				lang.warn_schedule.format(task['task_name_full'])
			)
			
		status, data = every_parse(task['every'])
		if not status:
			msg_warn(lang.warn_every.format(
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
				msg_warn(lang.warn_schedule.format(task['task_name_full']))

	def add_schedule(self, task):
		r'''
		*task* - dictionary with task parameters.  
		'''
		if app.is_cmd_task: return
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
				msg_warn(
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
				msg_warn(
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
			win32gui.ShowWindow(app.app_hwnd, win32con.SW_HIDE)
		for task in self.task_list_startup:
			self.run_task(task, caller=CALLER_STARTUP)
			
	def run_at_sys_startup(self):
		if win32api.GetTickCount() < 120_000:
			for task in self.task_list_sys_startup:
				self.run_task(task, caller=CALLER_SYS_STARTUP)
	
	def run_at_crontab_load(self):
		for task in self.task_list_crontab_load:
			self.run_task(task, caller=CALLER_LOAD)
	
	def task_opt_set(self, task_func_name:str, option:str, value):
		''' Sets the option for the task '''
		task = self.task_dict.get(task_func_name)
		if task == None:
			if is_dev():
				tprint(f'task not found: {task_func_name}, option: {option}')
			return
		task[option] = value

	def task_opt_get(self, task_func_name:str, option:str):
		''' Gets the option for the task '''
		task = self.task_dict.get(task_func_name)
		if task == None:
			if is_dev():
				tprint(f'task not found: {task_func_name}, option: {option}')
			return
		return task.get(option, 'task_opt_get error: option not found')

	def run_task(self, task:dict, caller:str=None, data=None
	, result:list=None, wait_event:threading.Event=None):
		r'''
		Logging, threading, error catching and other stuff.
		*task* - dict with task options
		*caller* - who actually launched the task.
			It can be 'hotkey', 'menu', 'scheduler', 'http' etc.,
			so you can find out inside the task function who
			started function this time.
		*data* - pass some data to task
		*result* - list in which we will place result of task. It is
			passed through all inner fuctions (`run_task_inner` and
			`catcher`).
		*wait_event* - for signaling somewhere that the task has finished  
		'''

		def run_task_inner(result:list=None):

			def catcher(result:list=None):
				nonlocal thread
				try:
					app.app_threads[thread.ident] = {
						'func': 'task: ' + task['task_func_name']
						, 'stime': dtime.now(), 'thread': thread
					}
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
					r = task['task_func'](**task_kwargs)
					if result != None: result.append(r)
					try:
						if ( t := tasks.task_dict.get(task['task_func_name'], {}) ):
							t['running'] = False
							t['thread'] = None
					except NameError:
						dev_print(f'"tasks" not exists for the task {task["task_func_name"]}')
					self.task_opt_set(task['task_func_name'], 'err_counter', 0)
					if wait_event: wait_event.set()
				except:
					try:
						if (
							t := tasks.task_dict.get(task['task_func_name'], {})
						):
							t['running'] = False
							t['thread'] = None
					except NameError:
						if is_dev():
							tprint('task stopped after reload: '
							+ task['task_func_name'])
					err_counter = self.task_opt_get(task['task_func_name']
					, 'err_counter') + 1
					if not result is None: result.append('task error')
					if err_counter <= self.task_opt_get(task['task_func_name']
					, 'err_threshold'):
						self.task_opt_set(task['task_func_name']
						, 'err_counter', err_counter)
						if is_dev():
							tprint(f'exception msg suppressed: {exc_text()}'
							, tname=task['task_func_name'], short=True)
					else:
						self.task_opt_set(task['task_func_name']
						, 'err_counter', 0)
						msg_err(lang.warn_task_error.format(
						task['task_name_full']) )
				_thread_pop('task', thread_id=thread.ident)
			if task['rule'] and (caller != tcon.CALLER_MENU):
				for rule in task['rule']:
					try:
						if not rule():
							return
					except:
						msg_err(lang.warn_rule_exc.format(task["task_name"]))
						return
			if task['log'] and caller != CALLER_CMDLINE:
				cs = f' ({caller})' if caller else ''
				con_log(f'task{cs}: {task["task_name_full"]}')
			thread = threading.Thread(target=catcher, daemon=daemon
			, name=task['task_name']
			, args=(result,) if task['result'] else () )
			thread.start()
			if task['result']: thread.join()
		if app.is_cmd_task and (caller != CALLER_CMDLINE): return
		if (
			(not self.enabled)
			and ( not task['hyperactive'])
			and caller != CALLER_MENU
		): return
		if task['single'] and task['running']: return
		daemon = (not caller in (CALLER_EXIT, CALLER_CMDLINE)) 
		if task['result'] and not (result is None):
			thread_start(run_task_inner, is_daemon=daemon, args=(result,)
			, err_msg=True, ident='app: run_task_inner: ' + task['task_name'])
		else:
			run_task_inner()

	def add_idle_task(self, task):
		if app.is_cmd_task: return
		dur = value_to_unit(task['idle'], 'ms')
		task['idle_dur'] = int(dur)
		task['idle_done'] = False
		self.task_list_idle.append(task)
	
	def add_event_handler(self, task):
		
		def event_handler(evt_handle):
			r'''
			We do all the work here since the handle is no longer valid after the callback completes.  

			See also #event notes
			'''
			context_sys = win32evtlog.EvtCreateRenderContext(
				win32evtlog.EvtRenderContextSystem
			)
			context_data = win32evtlog.EvtCreateRenderContext(
				win32evtlog.EvtRenderContextUser
			)
			event = win32evtlog.EvtRender(evt_handle
			, win32evtlog.EvtRenderEventValues, Context=context_sys)
			evt_data = win32evtlog.EvtRender(evt_handle
			, win32evtlog.EvtRenderEventValues, Context=context_data)
			prov_name, prov_name_type = event[win32evtlog.EvtSystemProviderName]
			msg = ''
			if prov_name_type == win32evtlog.EvtVarTypeNull:
				msg = '<null provider>'
				if is_dev():
					tprint('provider name null?', str_indent(event)
					, tname='event_handler')
			else:
				try:
					metadata = win32evtlog.EvtOpenPublisherMetadata(prov_name)
				except:
					msg = '<metadata exception>'
				else:
					try:
						msg = win32evtlog.EvtFormatMessage(
							metadata
							, evt_handle
							, win32evtlog.EvtFormatMessageEvent
						)
					except:
						msg = '<message exception>'
			self.run_task(task, caller=CALLER_EVENT
			, data=DataEvent(event, msg, evt_data))
			context_sys.close()
			context_data.close()
		
		def event_wait():
			while True:
				while True:
					try:
						events = win32evtlog.EvtNext(sub, Count=128)
					except pywintypes.error as err:
						if err.winerror in (6, 4317):
							return
						else:
							raise
					if len(events) == 0: break
					for evt in events: event_handler(evt)
				while True:
					wait = win32event.WaitForSingleObjectEx(signal, 1000, True)
					if wait == win32con.WAIT_OBJECT_0: break

		if app.is_cmd_task: return
		try:
			signal = win32event.CreateEvent(None, 0, 0, None)
			sub = win32evtlog.EvtSubscribe(
				ChannelPath=task['event_log']
				, SignalEvent=signal
				, Flags=win32evtlog.EvtSubscribeToFutureEvents
				, Query=task['event_xpath']
			)
			self.event_handlers.append((sub, signal))
			thread_start(
				event_wait
				, ident=f'app: event_wait ({task["task_func_name"]})'
			)
		except:
			dev_print('EvtSubscribe exception:' + str_indent(exc_text(6)) )
			msg_warn( lang.warn_event_format.format( task['task_name_full'] ) )

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
				msec = _idle_millis()
				if msec < self.idle_min:
					if afk:
						afk = False
						for task in self.task_list_idle:
							task['idle_done'] = False
				else:
					afk = True
					for task in self.task_list_idle:
						if task['idle_done']: continue
						if msec >= task['idle_dur']:
							self.run_task(task, caller=CALLER_IDLE)
							task['idle_done'] = True
			time.sleep(1.0)
			try:
				cur_thread_id = tasks.sched_thread_id
			except NameError:
				dev_print('tasks not exists')
				break

	def close(self):
		r'''
		Destructor.  
		Remove scheduler jobs, hotkey bindings, stop http server
		, close event handlers.  
		'''
		start = dtime.now()
		if self.http_server:
			self.http_server.shutdown()
			self.http_server.socket.close()
		keyboard.unhook_all()
		if self.global_hk:
			self.global_hk.unregister()
			self.global_hk.stop_listener()
			self.global_hk = None
		schedule.clear()
		for eh, signal in self.event_handlers:
			try:
				win32event.SetEvent(signal)
				eh.close()
			except Exception as err:
				dev_print(f'event close error: {err}')
		for hDir, dir_path in tuple(self.dir_change_stop.items()):
			msg = [dir_path]
			try:
				CancelIoEx(hDir.handle, None)
			except OSError as err:
				if err.winerror == 1168:
					msg.append(f'{err.strerror} ({err.winerror})')
				else:
					msg.append(f'CancelIoEx: {repr(err)}')
			except Exception as err:
					msg.append(f'CancelIoEx general: {repr(err)}')
			try:
				hDir.Close()
			except Exception as err:
				msg.append(f'Close: {repr(err)}')
			if is_dev() and len(msg) > 1:
				dev_print(str_indent(', '.join(msg)))
				tlog('[app] close: ' + ', '.join(msg))
		dev_print('close time: ' + time_diff_human(start, with_ms=True))
tasks:Tasks = None

def load_crontab(event=None)->bool:
	global tasks
	global crontab
	start = dtime.now()
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
					if is_dev(): qprint(f'permission error {attempt=}')
					time.sleep(.01)
				except:
					sys.modules['crontab'] = prev_crontab
					msg_err(lang.warn_crontab_reload, title=lang.menu_reload
					, source='load_crontab')
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
		running_tasks = []
		for rtask in run_bef_reload:
			if not (task := tasks.task_dict.get(rtask['task_func_name']) ):
				continue
			running_tasks.append(rtask['task_func_name'])
			task['thread'] = rtask['thread']
			task['last_start'] = rtask['last_start']
			task['running'] = rtask['running']
		tasks.enabled = app.enabled
		thread_start(tasks.run_at_crontab_load, err_msg=True
		, ident='app: run_at_crontab_load')
		if is_dev():
			tprint('load time: ' + time_diff_human(start, with_ms=True))
		gc.collect()
		return True
	except:
		msg_err(lang.warn_crontab_reload, title=lang.menu_reload)
		return False
	
def load_modules():
	'''
	(Re)Loads all application plugins and
	crontab extensions if any.
	'''

	global crontab
	setattr(sett, 'own_modules', {'plugins.constants'})
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
			msg_err(lang.warn_mod_reload.format(mdl_name)
			, title=lang.menu_reload, source='load_modules')
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
			for mdl_name_own in sett.own_modules:
				if hasattr(sys.modules.get(mdl_name_own), obj_name):
					setattr(sys.modules[mdl_name_own]
						, obj_name, decor_except_status(obj))
			if hasattr(crontab, obj_name):
				setattr(crontab, obj_name, decor_except_status(obj))
		sys.modules[mdl_name] = mdl

class Task:
	def __init__(self):
		self.name:str = ''
		self.every:str|tuple|list = ''
		self.func = None
		self.menu:bool = True
		self.submenu:str = ''
		self.status

def create_menu_item(menu, task, func=None, parent_menu=None):
	r'''
	*task* - task dict or menu item label  
	If *task* is a dictionary then *func* is *tasks.run_task*  
	*parent_menu* - for submenu items only.  
	'''
	if isinstance(task, dict):
		tname = task['task_name']
		if task['hotkey']:
			tname = f"{tname}\t{task['hotkey'].title()}"
		func = lambda evt, temp=task: tasks.run_task(task=temp
		, caller=CALLER_MENU)
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

	def CreatePopupMenu(self)->wx.Menu:
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
		print(f'{lang.menu_command_con}:')
		with SuppressPrint(): cmd = input()
		if not cmd: return
		try:
			val = eval(cmd)
		except:
			qprint('eval exception:', exc_name())
			return
		qprint(val)

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
		r'''
		Default action when left-clicking on the tray icon.
		'''
		if sett.kiosk and not keyboard.is_pressed(sett.kiosk_key): return
		if app.app_hwnd:
			if sett.hide_console:
				if win32gui.IsWindowVisible(app.app_hwnd):
					win32gui.ShowWindow(app.app_hwnd, win32con.SW_HIDE)
				else:
					show_app_window()
			else:
				show_app_window()

	def on_exit(self, event=None, force:bool=False
	, is_end_session:bool=False)->bool:
		r'''
		Returns `False` if user canceled exit.  
		*force* - do not display a warning dialog about running tasks.  
		*is_end_session* - logoff or shutdown.  
		'''
		TASKS_MSG_MAX = 10
		if is_end_session:
			force = True
			if is_dev():
				tprint(f'end of session')
				tlog(f'end of session')
		running_tasks = ()
		if not app.is_cmd_task:
			running_tasks = self.running_tasks(show_msg=False)
		if running_tasks:
			tasks_str = '\r\n'.join(
				tuple(
					t['task_name'] for t in running_tasks
				)[:TASKS_MSG_MAX]
			)
			if len(running_tasks) > TASKS_MSG_MAX:
				tasks_str += '\n...'
			if not force:
				if dialog(
					lang.warn_runn_tasks_msg.format( len(running_tasks) )
					+ '\n\n' + tasks_str
					, title=lang.menu_exit
					, buttons=(lang.button_close, lang.button_cancel)
					, return_button=True
				)[1] != lang.button_close:
					return False
		if not app.is_cmd_task and tasks.task_list_exit:
			tprint(
				lang.warn_on_exit + ': '
				 + ', '.join(
					t['task_name'] for t
					in tasks.task_list_exit
				 )
			)
			for task in tasks.task_list_exit:
				tasks.run_task(task, caller=CALLER_EXIT)
		qprint(lang.menu_exit)
		tasks.close()
		app.que_log.stop()
		app.que_print.stop()
		wx.CallAfter(self.Destroy)
		self.frame.Close()
		return True

	def running_tasks(self, show_msg:bool= True
	, event=None)->tuple:
		r'''
		Prints running tasks and shows dialog
		(if show_msg == True).  
		Returns a tuple of names of running tasks.  
		'''
		TASKS_MSG_MAX = 10
		running_tasks = tuple(
			t for t in tasks.task_dict.values() if t['running']
		)
		if is_dev():
			app_threads_print()
			app_win_show()
		if not running_tasks:
			if show_msg:
				dialog(lang.warn_no_run_tasks, title=lang.menu_list_run_tasks
				, timeout=3, wait=False)
			else:
				tprint('no running tasks', tname='app')
			return ()
		os_threads:dict[str, int] = {}
		for thr in threading.enumerate():
			if thr._target is None: continue
			os_threads[thr.name] = thr.native_id
		table = [('Task function', 'Exist', 'TID'
		, 'Start time', 'Running time')]
		nx_tasks:list = []
		for t in running_tasks:
			exist:str = 'Y'
			if not t['thread'] in os_threads:
				exist = 'N'
				nx_tasks.append(t)
			last_start = None
			duration = None
			if t['last_start']:
				last_start = t['last_start'].strftime('%Y.%m.%d %H:%M:%S')
				duration = time_diff_human(t['last_start'])
			module = t['task_func'].__module__
			module = '' if module == 'crontab' else module + '.' 
			table.append((
				module + t['task_func_name']
				, exist
				, os_threads.get(t['thread'], '?')
				, last_start
				, duration
			))
		if len(table) > 1:
			qprint(lang.warn_runn_tasks_con + ':')
			table_print(table, use_headers=True)
		if (not show_msg) or is_dev(): return running_tasks
		tasks_str = '\r\n'.join(
			tuple(t['task_name'] for t in running_tasks)[:TASKS_MSG_MAX]
		)
		if len(running_tasks) > TASKS_MSG_MAX:
			tasks_str += '\r\n...'
		buttons = (lang.dlg_nx_tasks,) if nx_tasks else None
		choice = dialog(tasks_str, buttons=buttons, timeout='10 sec'
		, wait=(True if nx_tasks else False))
		if choice != 1000: return ()
		for task in nx_tasks:
			tasks.task_dict.pop(task['task_func_name'], None)
		return ()

	def on_edit_crontab(self, event=None):
		proc_start(sett.editor, os.path.join(APP_PATH, 'crontab.py'))

	def on_edit_settings(self, event=None):
		proc_start(sett.editor, os.path.join(APP_PATH, r'settings.ini'))

	def on_disable(self, event=None, state:bool|None=None):
		if state == None: state = not tasks.enabled
		tasks.enabled = state
		app.enabled = state
		if state:
			set_title(APP_NAME)
			con_log(f'{APP_NAME} enabled')
		else:
			set_title(f'{APP_NAME} (disabled)')
			con_log(f'{APP_NAME} disabled')
		self.set_icon(dis=not state)
	
	def on_restart(self, event=None, force:bool=False):

		ext = '.exe' if getattr(sys, 'frozen', False) else '.py'
		fpath = os.path.join(APP_PATH, APP_NAME + ext)
		args = ' '.join(sys.argv[1:])
		is_exit = self.on_exit()
		if not force and not is_exit: return
		file_open(fpath, parameters=args)

class App(wx.App):

	def OnInit(self):
		self.enabled = True
		self.app_threads = {}
		self.frame=wx.Frame(None, style=wx.DEFAULT_FRAME_STYLE
			| wx.STAY_ON_TOP)
		self.taskbaricon = TaskBarIcon(self.frame)
		self.show_window = self.taskbaricon.on_left_down
		self.app_pid = win32process.GetCurrentProcessId()
		self.app_hwnd:int = 0
		self.frame.Bind(wx.EVT_END_SESSION
		, lambda: self.taskbaricon.on_exit(is_end_session=True) )
		self.cmd_args:argparse.Namespace = argparse.Namespace()
		self.is_cmd_task:bool = False
		self.load_crontab = load_crontab
		self.dir = APP_PATH
		return True
	
	def win_save(self):
		'Find and save handle of console window'
		show_warn:int = (not sett.dev) \
		and (getattr(self.cmd_args, 'task', None) == None)
		hwnd_list = win_find(APP_NAME)
		if len(hwnd_list) == 1:
			self.app_hwnd = hwnd_list[0]
		elif len(hwnd_list) > 1:
			self.app_hwnd = hwnd_list[0]
			if not show_warn: return
			msg_warn(lang.warn_too_many_win.format(APP_NAME, len(hwnd_list) ) )
		else:
			if show_warn: msg_warn(f'None of {APP_NAME} windows was found')

	def InitLocale(self):
		' Override with nothing (or impliment local if actually needed)'
		pass
	
	def exit(self, force:bool=False):
		self.taskbaricon.on_exit(force=force)

def show_app_window():
	try:
		win32gui.ShowWindow(app.app_hwnd, win32con.SW_RESTORE)
		win32gui.SetForegroundWindow(app.app_hwnd)
	except Exception as e:
		dev_print(f'show window exception: {e}')

def every_parse(every:str|list|tuple)->tuple[bool, list]:
	r'''
	Examples:

		from taskopy import every_parse
		for es in ('5m', '5M', '5 m', '5 min', '5min'
		, '5 minutes', 'mon 05:45', 'Mon 05:45'
		, 'day 17:45', 'hour :30', 'h:30', ('5m', '5s')
		, '5 to 6 min', '5to6min'):
			asrt( every_parse(es)[0], True )
		for es in ('5y', '5', '5 mins', '5mins', 5
		, 'mon 5:45', 'hour 0:30', ('5m', 'hour')):
			asrt( every_parse(es)[0], False )
		
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

def con_key_listener():
	r'''
	Poll the console input for keystrokes.
	'''
	while True:
		if msvcrt.kbhit():
			key = msvcrt.getch()
			match key:
				case b'\x11':
					app.exit()
				case b'\x12':
					app.load_crontab()
				case b'\x14':
					app.taskbaricon.running_tasks(show_msg=False)
				case b'\x05':
					app.taskbaricon.run_command()
		time.sleep(.1)

def main():

	def wait_exit(event, timeout=60.0):
		event.wait(timeout)
		app.exit(force=True)

	global app
	global tasks
	global sett
	global lang
	set_title(APP_NAME)
	cmd_parser = argparse.ArgumentParser()
	cmd_parser.add_argument('-dev', action='store_true'
	, help='Enable debug output')
	cmd_parser.add_argument('-task', type=str
	, help='A task to run and quit')
	cmd_parser.add_argument('-data', type=str
	, help='Any data for a task started with *-task* option')
	try:
		cmd_args = cmd_parser.parse_args()
	except SystemExit:
		if '-h' in sys.argv or '--help' in sys.argv:
			sys.exit(0)
		print('\nERROR: invalid command-line arguments. Quit.\n')
		sys.exit(2)
	try:
		sett = Settings(def_sett=APP_SETTINGS)
	except Exception as e:
		print(f'Settings load error: {e}')
		msg_err('Cannot load settings')
		sys.exit(1)
	__builtins__.sett = sett
	lang = Language(sett.language)
	__builtins__.lang = lang
	if cmd_args.task: sett.kiosk = True
	if sett.kiosk:
		sett.dev = False
		cmd_args.dev = False
		sett.hide_console = True
	print(f'{APP_NAME} {APP_VERSION} (Python {sys.version})')
	print(lang.load_homepage)
	print(lang.load_donate + '\n\n')
	try:
		app = App(False)
		__builtins__.app = app
		app.que_print:TQueue = TQueue(consumer=print, max_size=8192)
		app.que_log:TQueue = TQueue(consumer=_tlog, max_size=8192)
		app.is_cmd_task = not cmd_args.task is None
		app.cmd_args = cmd_args
		app.win_save()
		if load_crontab():
			if cmd_args.task:
				event = threading.Event()
				thread_start(wait_exit, args=(event,), ident='app: wait_exit')
				task_start(cmd_args.task, caller=CALLER_CMDLINE
				, data=cmd_args.data, wait_event=event)
				app.MainLoop()
				return
			tasks.run_at_startup()
			tasks.run_at_sys_startup()
		thread_start(con_key_listener, ident='app: console key listener')
		app.MainLoop()
	except:
		msg_err('General exception')
		input('Press Enter to exit...')


if __name__ == '__main__': main()
