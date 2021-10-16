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
tasks = None
crontab = None
sett = None
lang = None
if getattr(sys, 'frozen', False):
	APP_PATH = os.path.dirname(sys.executable)
	os.chdir(APP_PATH)
	sys.path.append(APP_PATH)
else:
	APP_PATH = os.getcwd()

APP_ICON = r'resources\icon.png'
APP_ICON_DIS = r'resources\icon_dis.png'
TASK_DATE_FORMAT = \
	r'^(\d\d\d\d|\*)\.(\d\d|\*)\.(\d\d|\*) (\d\d|\*):(\d\d|\*)$'
PLUGIN_SOURCE = 'plugins\\*.py'

set_title = win32api.SetConsoleTitle
	
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
			for setting in section.items():
				if setting[1].lower() in ('true', 'yes'):
					self.__dict__[setting[0]] = True
				elif setting[1].lower() in ('false', 'no'):
					self.__dict__[setting[0]] = False
				elif setting[1].isdigit():
					self.__dict__[setting[0]] = int(setting[1])
				elif setting[1].replace('.', '', 1).isdigit():
					try:
						self.__dict__[setting[0]] = float(setting[1])
					except:
						self.__dict__[setting[0]] = setting[1]
				else:
					self.__dict__[setting[0]] = setting[1]
		for setting in APP_SETTINGS:
			self.__dict__.setdefault(setting[0], setting[1])

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
			for a in range(100):
				try:
					tmp_crontab = importlib.import_module('crontab')
					break
				except PermissionError:
					dev_print(f'permission error {a}')
					time.sleep(.01)
				except:
					trace_li = traceback.format_exc().splitlines()
					trace_str = '\n'.join(trace_li[-3:])
					con_log(traceback.format_exc())
					sys.modules['crontab'] = prev_crontab
					msgbox_warning(
						f'{lang.warn_crontab_reload}:\n\n{trace_str}'
						, title=lang.menu_reload)
					return False
			else:
				raise Exception('No more attempts to reload crontab')
			for task in tasks.task_list:
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
		for rtask in run_bef_reload:
			dev_print('still running:', rtask['task_function_name'])
			for task in tasks.task_list:
				if task['task_function_name'] != \
				rtask['task_function_name']: continue
				task['thread'] = rtask['thread']
				task['last_start'] = rtask['last_start']
				task['running'] = rtask['running']
		tasks.run_at_crontab_load()
		tasks.enabled = app.enabled
		return True
	except:
		trace_li = traceback.format_exc().splitlines()
		trace_str = '\n'.join(trace_li[-3:])
		con_log(traceback.format_exc())
		msgbox_warning(
			f'{lang.warn_crontab_reload}:\n\n{trace_str}'
			, title=lang.menu_reload)
		return False
	
def load_modules():
	''' (Re)Loads all application plugins and additional
		crontab modules if any.
	'''
	global crontab
	if not hasattr(sett, 'own_modules'):
		sett.own_modules = {'plugins.constants'}
		for obj_name, obj in crontab.__dict__.items():
			if (
				hasattr(obj, '__module__')
				and obj.__module__ != 'crontab'
				and obj.__module__ != '__main__'
				and hasattr(sys.modules[obj.__module__], '__file__')
			):
				try:
					if not os.path.relpath(
						inspect.getfile(sys.modules[obj.__module__])
					).startswith('.'):
						sett.own_modules.add(obj.__module__)
				except ValueError:
					continue
	for mdl_name in sett.own_modules:
		prev_mdl = sys.modules.pop(mdl_name)
		try:
			tmp_mdl = importlib.import_module(mdl_name)
		except PermissionError:
			tprint(f'{mdl_name} permission error')
		except:
			trace_li = traceback.format_exc().splitlines()
			trace_str = '\n'.join(trace_li[-3:])
			con_log(traceback.format_exc())
			sys.modules[mdl_name] = prev_mdl
			msgbox_warning(
				'{}:\n\n{}'.format(
					lang.warn_mod_reload.format(mdl_name)
					, trace_str
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
				or inspect.ismodule(obj)
				or not mdl_name in getattr(obj, '__module__', mdl_name)
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

class Tasks:
	''' Tasks from crontab and they properties '''
	def __init__(self):
		self.enabled = True
		self.task_list = []
		self.task_list_menu = []
		self.task_list_submenus = []
		self.task_list_startup = []
		self.task_list_left_click = []
		self.task_list_sys_startup = []
		self.task_list_http = []
		self.task_list_idle = []
		self.task_list_crontab_load = []
		self.task_list_exit = []
		self.file_change_stop = []
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
			for opt in TASK_OPTIONS:
				param = params.get(opt[0])
				if param is None:
					task_opts[opt[0]] = opt[1]
				else:
					task_opts[opt[0]] = param.default
			if not task_opts['task']: continue
			if not task_opts['active']: continue
			task_opts['task_function'] = task_obj
			task_opts['task_function_name'] = item
			if task_opts['task_name']:
				task_opts['task_name_full'] = f'{item} ({task_opts["task_name"]})'
			else:
				if item[0].isupper():
					task_opts['task_name'] = item.replace('_', ' ')
				else:
					task_opts['task_name'] = item.replace('_', ' ').capitalize()
				task_opts['task_name_full'] = task_opts['task_name']
			if task_opts['schedule']:
				self.add_schedule(task_opts)
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
				self.add_file_change_watch(task_opts, 3)
			self.task_list.append(task_opts)
			if task_opts['menu']:
				if task_opts['submenu']:
					for m in self.task_list_submenus:
						if m[0] == task_opts['submenu']:
							m[1].append(task_opts)
							break
					else:
						self.task_list_submenus.append(
							[task_opts['submenu'], [task_opts]]
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
		self.task_list_menu.sort( key=lambda k: k['task_name'].lower() )
		self.task_list_submenus.sort( key=lambda k: k[0].lower() )
		for subm in self.task_list_submenus:
			subm[1].sort( key=lambda k: k['task_name'].lower() )
		left_click_tasks_count = len(self.task_list_left_click)
		if left_click_tasks_count > 1:
			msgbox_warning(
				lang.warn_left_click.format(
					', '.join(
						[t['task_name'] for t in self.task_list_left_click]
					)
				)
			)
		elif left_click_tasks_count == 0:
			app.taskbaricon.Bind(
				wx.adv.EVT_TASKBAR_LEFT_DOWN
				, app.taskbaricon.on_left_down
			)
		if self.global_hk:
			t = threading.Thread(target=self.global_hk.listen, daemon=True)
			t.start()
			self.global_hk_thread_id = t.ident
		if self.task_list_http:
			threading.Thread(
				target=http_server_start
				, args=(self, )
				, daemon=True
			).start()
		t = threading.Thread(target=self.run_scheduler, daemon=True)
		t.start()
		self.sched_thread_id = t.ident
		dev_print(f'Total number of tasks: {len(self.task_list)}')
	
	def add_hotkey(self, task):
		def hk_error(error):
			con_log(error)
			msgbox_warning(
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
	
	def add_file_change_watch(self, task:dict, on_action:int):
		'Watch for changes in directory'
		ACTIONS = {
			1: 'created'
			, 2: 'deleted'
			, 3: 'updated'
			, 4: 'renamed from something'
			, 5: 'renamed to something'
		}
		WAIT_INTERVAL = '100 msec'
		FILE_LIST_DIRECTORY = 0x0001
		BUFFER_LENGTH = 1024

		def file_watch(task:dict, on_action:int
		, stop_event:threading.Event):
			hDir = win32file.CreateFile (
				file_dir(task['on_file_change'])
				, FILE_LIST_DIRECTORY
				, win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE
				, None
				, win32con.OPEN_EXISTING
				, win32con.FILE_FLAG_BACKUP_SEMANTICS
				, None
			)
			fullpath = task['on_file_change']
			filename = file_name(fullpath)
			prev_results = [(0, None)]
			while not stop_event.is_set():
				results = win32file.ReadDirectoryChangesW(
					hDir,
					BUFFER_LENGTH,
					False, 
					win32con.FILE_NOTIFY_CHANGE_SIZE,
					None,
					None
				)
				if stop_event.is_set(): return
				if results[0][1] == prev_results[0][1] \
				and len(results) > 1:
					prev_results = results
					continue
				prev_results = results
				for action, fname in results[:1]:
					if filename != fname:
						continue
					if action != on_action:
						continue
					if action in (1, 3):
						file_lock_wait(fullpath, wait_interval=WAIT_INTERVAL)
					self.run_task(task, caller=CALLER_FILE_CHANGE)

		stop_event = threading.Event()
		self.file_change_stop.append(stop_event)
		threading.Thread(
			target=file_watch
			, args=(task, on_action, stop_event)
			, daemon=True
		).start()

	def add_schedule(self, task):
		''' task - dict with task options
		'''
		intervals = task['schedule']
		if isinstance(intervals, str): intervals = [intervals]
		for inter in intervals:
			try:
				sched_rule = (
					'schedule.' + inter
					+ f'.do(self.run_task, task=task, caller="{CALLER_SCHEDULER}")'
				)
				eval(sched_rule)
			except Exception as e:
				con_log(repr(e))
				msgbox_warning(
					lang.warn_schedule.format(task['task_name_full'])
					+ ':\n' + inter
				)

	def add_schedule_date(self, task):
		''' task - dict with task options '''

		def date_replace_ast(date:str)->str:
			'''	Replace asterisk to current date time value.
				date_replace_ast('*.*.01 12:30')
				->	'2020.10.01 12:30'
			'''
			if not '*' in date: return date
			date = date.replace('.', ' ').replace(':', ' ')
			new_date_li = list( time_now().timetuple() )
			for pos, value  in enumerate( date.split() ):
				if value != '*': new_date_li[pos] = value
			return '{:0>4}.{:0>2}.{:0>2} {:0>2}:{:0>2}' \
				.format(*new_date_li)

		def run_task_date(date:str, task:dict):
			if time_now_str('%Y.%m.%d %H:%M') != \
			date_replace_ast(date):
				return
			if task['last_start']:
				if time_diff(
					task['last_start']
					, time_now()
					, unit='min'
				) < 1:
					return
			self.run_task(task=task, caller=CALLER_SCHEDULER)

		dates = task['date']
		if isinstance(dates, str): dates = [dates]
		for date in dates:
			if not re_match(date, TASK_DATE_FORMAT):
				msgbox_warning(
					lang.warn_date_format.format(
						task['task_name_full']
						, date
					)
				)
				continue
			schedule.every().second.do(
				run_task_date, date=date, task=task)

	def run_at_startup(self):
		if sett.hide_console:
			window_hide(app.app_hwnd)
		for task in self.task_list_startup:
			self.run_task(task, caller=CALLER_STARTUP)
			
	def run_at_sys_startup(self):
		if uptime.uptime() < 120:
			for task in self.task_list_sys_startup:
				self.run_task(task, caller=CALLER_SYS_STARTUP)
	
	def run_at_crontab_load(self):
		for task in self.task_list_crontab_load:
			self.run_task(task, caller=CALLER_LOAD)
	
	def task_opt_set(self, task_function_name:str, option:str, value):
		''' Set option from task dict in tasks.task_list
		'''
		for task in self.task_list:
			if task['task_function_name'] == task_function_name:
				task[option] = value
				break

	def task_opt_get(self, task_function_name:str, option:str):
		''' Get option from task in tasks.task_list
		'''
		for task in self.task_list:
			if task['task_function_name'] == task_function_name:
				return task.get(option
					, 'task_opt_get error: option not found')
		else:
			return 'task_opt_get error: task not found'

	def run_task(self, task:dict, caller:str=None, data=None
	, result:list=None):
		''' Logging, threading, error catching and other stuff.
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
					self.task_opt_set(task['task_function_name']
						, 'running', True)
					self.task_opt_set(task['task_function_name']
						, 'thread', threading.current_thread().name)
					task_kwargs = {}
					func_args = [
						k.lower()
						for k in inspect.signature(
							task['task_function']
						).parameters.keys()
					]
					if 'caller' in func_args:
						task_kwargs['caller'] = caller
					if 'data' in func_args:
						task_kwargs['data'] = data
					task['last_start'] = datetime.datetime.now()
					if task['no_print']:
						with SuppressPrint():
							r = task['task_function'](**task_kwargs)
					else:
						r = task['task_function'](**task_kwargs)
					if r:
						if not result is None:
							result.append(r)
					for t in tasks.task_list:
						if t['task_function_name'] == \
						task['task_function_name']:
							t['running'] = False
							t['thread'] = None
							break
					self.task_opt_set(task['task_function_name']
						, 'err_counter', 0)
				except Exception:
					for t in tasks.task_list:
						if t['task_function_name'] == task['task_function_name']:
							t['running'] = False
							t['thread'] = None
							break
					err_counter = self.task_opt_get(
						task['task_function_name']
						, 'err_counter'
					) + 1
					trace_li = traceback.format_exc().splitlines()
					trace_str = '\n'.join(trace_li[-3:])
					con_log(
						f'Error in task: {task["task_name_full"]}\n'
						+ traceback.format_exc()
					)
					if not result is None:
						result.append('task error')
					if err_counter > self.task_opt_get(
						task['task_function_name']
						, 'err_threshold'
					):
						dev_print(f'err_counter={err_counter}')
						self.task_opt_set(task['task_function_name']
										, 'err_counter', 0)
						msgbox_warning(
							lang.warn_task_error.format(task['task_name_full'])
							+ f':\n{trace_str}'
						)
					else:
						self.task_opt_set(task['task_function_name']
										, 'err_counter', err_counter)
			if (not self.enabled) \
			and ( not task['hyperactive'] ): return
			if task['single']:
				if task['running']: return
			if callable(task['rule']):
				try:
					r = task['rule']()
				except:
					dev_print(f'{task["task_name"]} rule exception')
					r = False
				if not r:
					dev_print(f'{task["task_name"]} canceled by rule')
					return
			if task['log']:
				cs = f' ({caller})' if caller else ''
				con_log(f'task{cs}: {task["task_name_full"]}')
			if task['result']:
				t = threading.Thread(target=catcher, args=(result,)
				, daemon=True)
				t.start()
				t.join()
			else:
				threading.Thread(target=catcher, daemon=True).start()
		if task['result'] and not result is None:
			threading.Thread(
				target=run_task_inner
				, args=(result,)
				, daemon=True
			).start()
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
			msgbox_warning(
				lang.warn_event_format.format( task['task_name_full'] )
			)

	def run_scheduler(self):
		time.sleep(0.01)
		local_id = tasks.sched_thread_id
		afk = True
		if self.task_list_idle:
			afk = False
			self.idle_min = min([t['idle_dur'] for t in self.task_list_idle])
		while (tasks.sched_thread_id == local_id):
			schedule.run_pending()
			if self.task_list_idle:
				ms = int(uptime.uptime() * 1000) - win32api.GetLastInputInfo()
				if ms < self.idle_min:
					if afk:
						dev_print('user is back')
						afk = False
						for task in self.task_list_idle: task['idle_done'] = False
				else:
					afk = True
					for task in self.task_list_idle:
						if task['idle_done']: continue
						if ms >= task['idle_dur']:
							self.run_task(task, caller=CALLER_IDLE)
							task['idle_done'] = True
			time.sleep(1)

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
		for es in self.file_change_stop: es.set()

def create_menu_item(menu, task, func=None, parent_menu=None):
	''' Task - task dict or menu item label
		If task is dict then func = tasks.run_task
		parent_menu - only for submenu items.
	'''
	if isinstance(task, dict):
		tn = task['task_name']
		if task['hotkey']:
			tn = f"{tn}\t{task['hotkey'].title()}"
		func = lambda evt, temp=task: tasks.run_task(task=temp, caller=CALLER_MENU)
	else:
		tn = task
	item = wx.MenuItem(menu, -1, tn)
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
				for task in tasks.task_list:
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
			icon_text = '\n'.join(
				[f'{k}{v}' for k, v in self.text_dic.items()])
		self.SetIcon(self.icon_dis if dis else self.icon, icon_text)
	
	def show_menu_wait(self, event=None):
		print('show_menu 3 sec')
		self.frame.Raise()
		self.frame.SetFocus()
		menu = self.CreatePopupMenu()
		print(self.frame.PopupMenu(menu, pos=(0, 0)))
		menu.Destroy()

	def on_left_down(self, event=None):
		''' Default action on left click to tray icon
		'''
		if sett.kiosk and not keyboard.is_pressed(sett.kiosk_key): return
		if app.app_hwnd:
			if sett.hide_console:
				if window_is_visible(app.app_hwnd):
					window_hide(app.app_hwnd)
				else:
					show_app_window()
			else:
				show_app_window()

	def on_exit(self, event=None)->bool:
		TASKS_MSG_MAX = 5
		running_tasks = self.running_tasks(show_msg=False)
		if running_tasks:
			tasks_str = '\r\n'.join(
				[t['task_name'] for t in running_tasks]
				[:TASKS_MSG_MAX]
			)
			if len(running_tasks) > TASKS_MSG_MAX:
				tasks_str += '\r\n...'
			if dialog(
				lang.warn_runn_tasks_msg.format( len(running_tasks) )
				+ '\r\n\r\n' + tasks_str
				, title=lang.menu_exit
				, buttons=[lang.button_close, lang.button_cancel]
				, return_button=True
			)[1] != lang.button_close:
				return False
		for task in tasks.task_list_exit:
			tasks.run_task(task, caller=CALLER_EXIT)
		con_log(lang.menu_exit)
		tasks.close()
		wx.CallAfter(self.Destroy)
		self.frame.Close()
		return True

	def running_tasks(self, show_msg:bool= True
	, event=None)->list:
		''' Prints running tasks and shows dialog
			(if show_msg == True).
			Returns list of running task names.
		'''
		TASKS_MSG_MAX = 10
		running_tasks = [t for t in tasks.task_list
			if t['running'] ]
		if not running_tasks:
			if show_msg:
				dialog(lang.warn_no_run_tasks
					, title=lang.menu_list_run_tasks
					, timeout=3
					, wait=False)
			return
		cur_threads = []
		for thread in threading.enumerate():
			if thread._target is None: continue
			cur_threads.append(thread.name)
		table = [['Task function', 'Thread'
		, 'Start time', 'Running time']]
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
			table.append([
				t['task_function_name']
				, thread
				, last_start
				, duration
			])
		if len(table) > 1:
			print(lang.warn_runn_tasks_con + ':')
			table_print(table, use_headers=True)
		if not show_msg: return running_tasks
		tasks_str = '\r\n'.join(
			[t['task_name'] for t in running_tasks]
			[:TASKS_MSG_MAX]
		)
		if len(running_tasks) > TASKS_MSG_MAX:
			tasks_str += '\r\n...'
		dialog(tasks_str, timeout=10, wait=False)

	def on_edit_crontab(self, event=None):
		app_start(sett.editor, os.path.join(APP_PATH, 'crontab.py'))

	def on_edit_settings(self, event=None):
		app_start(sett.editor, os.path.join(APP_PATH, r'settings.ini'))

	def on_disable(self, event=None):
		tasks.enabled = not tasks.enabled
		app.enabled = tasks.enabled
		if tasks.enabled:
			set_title(APP_NAME)
			con_log('Enabled')
		else:
			set_title(f'Disabled {APP_NAME}')
			con_log('Disabled')
		self.set_icon(not tasks.enabled)
	
	def on_restart(self, event=None):
		if not self.on_exit(): return
		dev = None
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
		hwnd_list = window_find(APP_NAME)
		if len(hwnd_list) == 1:
			self.app_hwnd = hwnd_list[0]
		elif len(hwnd_list) > 1:
			self.app_hwnd = hwnd_list[0]
			if sett.dev:
				msgbox_warning(
					lang.warn_too_many_win.format(
					APP_NAME, len(hwnd_list) )
				)
		else:
			self.app_hwnd = 0
			if sett.dev:
				msgbox_warning(f'None of {APP_NAME} windows was found')
		return True

	def popup_menu_hk(self):
		tprint('app menu by hotkey')
		self.frame.SetFocus()
		time.sleep(0.1)
		self.frame.PopupMenu(self.taskbaricon.CreatePopupMenu())

def show_app_window():
	try:
		win32gui.ShowWindow(app.app_hwnd, win32con.SW_RESTORE)
		win32gui.SetForegroundWindow(app.app_hwnd)
	except Exception as e:
		dev_print(f'show window exception: {e}')

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
		msgbox_warning(f'Cannot load settings:\n{repr(e)}')
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
		trace_li = traceback.format_exc().splitlines()
		trace_str = '\n'.join(trace_li[-3:])
		msg = f'\nGeneral exception:\n\n{repr(e)}\n\n{trace_str}'
		print(msg)
		msgbox_warning(msg)
		input('Press Enter to exit...')
	except KeyboardInterrupt:
		tprint('Interrupted by keyboard')
		time.sleep(2)


if __name__ == '__main__': main()
