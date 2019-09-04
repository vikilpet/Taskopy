import time
import sys
import os
import importlib
import traceback
import threading
import inspect
import configparser
import wx.adv
import wx
import ctypes
import schedule
import keyboard
import win32api
import win32gui
import win32con
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
app = None
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

set_title = ctypes.windll.kernel32.SetConsoleTitleW
	
class Settings:
	''' Load global settings from settings.ini
		Settings from all sections are collected.
	'''
	def __init__(s):
		config = configparser.ConfigParser()
		config.optionxform = str
		config.read(r'settings.ini', encoding='utf-8-sig')
		for section in config._sections.values():
			for setting in section.items():
				if setting[1].lower() in ('true', 'yes'):
					s.__dict__[setting[0]] = True
				elif setting[1].lower() in ('false', 'no'):
					s.__dict__[setting[0]] = False
				elif setting[1].isdigit():
					s.__dict__[setting[0]] = int(setting[1])
				elif setting[1].replace('.', '', 1).isdigit():
					try:
						s.__dict__[setting[0]] = float(setting[1])
					except:
						s.__dict__[setting[0]] = setting[1]
				else:
					s.__dict__[setting[0]] = setting[1]
		for setting in APP_SETTINGS:
			s.__dict__.setdefault(setting[0], setting[1])

def load_crontab(event=None)->bool:
	global tasks
	global crontab
	con_log(f'{lang.load_crontab} {os.getcwd()}')
	try:
		if sys.modules.get('crontab') is None:
			crontab = importlib.import_module('crontab')
		else:
			tasks.close()
			del sys.modules['crontab']
			del crontab
			crontab = importlib.import_module('crontab')
		tasks = Tasks()
		tasks.enabled = app.enabled
		return True
	except Exception as e:
		trace_li = traceback.format_exc().splitlines()
		trace_str = '\n'.join(trace_li[-3:])
		con_log(traceback.format_exc())
		msgbox_warning(f'{lang.warn_crontab_reload}:\n\n{trace_str}')
		return False

class SuppressPrint:
	def __enter__(self):
		self._original_stdout = sys.stdout
		sys.stdout = open(os.devnull, 'w')

	def __exit__(self, exc_type, exc_val, exc_tb):
		sys.stdout.close()
		sys.stdout = self._original_stdout

class Tasks:
	''' Tasks from crontab and they properties '''
	def __init__(s):
		s.enabled = True
		s.task_list = []
		s.task_list_menu = []
		s.task_list_submenus = []
		s.task_list_startup = []
		s.task_list_left_click = []
		s.task_list_sys_startup = []
		s.task_list_http = []
		s.http_server = None
		s.global_hk = None
		s.global_hk_thread_id = None
		for item in dir(crontab):
			task_obj = getattr(crontab, item)
			if not callable(task_obj): continue
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
				s.add_schedule(task_opts)
			if task_opts['hotkey']: s.add_hotkey(task_opts)
			if task_opts['left_click']:
				s.task_list_left_click.append(task_opts)
				app.taskbar_icon.Bind(
					wx.adv.EVT_TASKBAR_LEFT_DOWN
					, lambda evt, temp=task_opts:
						s.run_task(task=temp, caller='left_click')
				)
			if task_opts['startup']:
				s.task_list_startup.append(task_opts)
			if task_opts['sys_startup']:
				s.task_list_sys_startup.append(task_opts)
			s.task_list.append(task_opts)
			if task_opts['menu']:
				if task_opts['submenu']:
					for m in s.task_list_submenus:
						if m[0] == task_opts['submenu']:
							m[1].append(task_opts)
							break
					else:
						s.task_list_submenus.append(
							[task_opts['submenu'], [task_opts]]
						)
				else:
					s.task_list_menu.append(task_opts)
			if task_opts['http']:
				s.task_list_http.append(task_opts)
		s.task_list_menu.sort( key=lambda k: k['task_name'].lower() )
		s.task_list_submenus.sort( key=lambda k: k[0].lower() )
		for subm in s.task_list_submenus:
			subm[1].sort( key=lambda k: k['task_name'].lower() )
		lc_count = len(s.task_list_left_click)
		if lc_count > 1:
			msgbox_warning(lang.warn_left_click.format(
				', '.join(
					[t['task_name'] for t in s.task_list_left_click]
				)
			))
		elif lc_count == 0:
			app.taskbar_icon.Bind(
				wx.adv.EVT_TASKBAR_LEFT_DOWN
				, app.taskbar_icon.on_left_down
			)
		if s.global_hk:
			t = threading.Thread(target=s.global_hk.listen, daemon=True)
			t.start()
			s.global_hk_thread_id = t.ident
		if s.task_list_http:
			threading.Thread(
				target=http_server_start
				, args=(sett, s)
				, daemon=True
			).start()
		t = threading.Thread(target=s.run_scheduler, daemon=True)
		t.start()
		s.sched_thread_id = t.ident
		if sett.developer: print(f'Total tasks: {len(s.task_list)}')
	
	def add_hotkey(s, task):
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
				if not s.global_hk:
					s.global_hk = GlobalHotKeys()
				s.global_hk.register(
					task['hotkey']
					, func=s.run_task
					, func_args=[task, 'hotkey']
				)
			except Exception as e:
				hk_error(repr(e))
		else:
			try:
				keyboard.add_hotkey(
					hotkey=task['hotkey'].lower()
					, callback=s.run_task
					, suppress=False
					, args=[task, 'hotkey']
				)
			except Exception as e:
				hk_error(repr(e))
	
	def add_schedule(s, task):
		''' task - dict with task options
		'''
		intervals = task['schedule']
		if type(intervals) is str: intervals = [intervals]
		for inter in intervals:
			try:
				sched_rule = (
					'schedule.' + inter + f'.do(s.run_task, task=task, caller="scheduler")'
				)
				eval(sched_rule)
			except Exception as e:
				con_log(repr(e))
				msgbox_warning(
					lang.warn_schedule.format(task['task_name_full'])
					+ ':\n' + inter
				)

	def run_at_startup(s):
		if sett.hide_console:
			if sett.developer: print(f'hide {app.app_hwnd}')
			window_hide(app.app_hwnd)
		for task in s.task_list_startup:
			s.run_task(task, caller='startup')
			
	def run_at_sys_startup(s):
		if win32api.GetTickCount() < (6 * 60 * 1000):
			for task in s.task_list_sys_startup:
				s.run_task(task, caller='sys_startup')
	
	def task_opt_set(s, task_function_name:str, option:str, value):
		''' Set option from task dict in tasks.task_list
		'''
		for task in s.task_list:
			if task['task_function_name'] == task_function_name:
				task[option] = value
				break

	def task_opt_get(s, task_function_name:str, option:str):
		''' Get option from task in tasks.task_list
		'''
		for task in s.task_list:
			if task['task_function_name'] == task_function_name:
				return task.get(option
						, 'task_opt_get error: option not found')
		else:
			return 'task_opt_get error: task not found'

	def run_task(s, task:dict, caller:str=None, data=None
				, result:list=None):
		''' Logging, threading, error catching and other stuff.
			task - dict with task options
			caller - who actually launched the task.
				It can be 'hotkey', 'menu', 'scheduler', 'http' etc.,
				so you can find out inside the task function who started function this time.
			data - pass some data to task
			result - list in which we will place result of task. It is
				passed through all inner fuctions (run_task_inner and
				catcher).
		'''
		def run_task_inner(result:list=None):
			def catcher(result:list=None):
				try:
					s.task_opt_set(task['task_function_name'], 'running', True)
					task_kwargs = {}
					func_args = inspect.signature(task['task_function']).parameters.keys()
					if 'caller' in func_args:
						task_kwargs['caller'] = caller
					if 'data' in func_args:
						task_kwargs['data'] = data
					if task['no_print']:
						with SuppressPrint():
							r = task['task_function'](**task_kwargs)
					else:
						r = task['task_function'](**task_kwargs)
					if r:
						if not result is None:
							result.append(r)
					s.task_opt_set(task['task_function_name'], 'running', False)
					s.task_opt_set(task['task_function_name'], 'err_counter', 0)
				except Exception:
					s.task_opt_set(task['task_function_name']
									, 'running', False)
					err_counter = s.task_opt_get(
						task['task_function_name']
						, 'err_counter'
					) + 1
					trace_li = traceback.format_exc().splitlines()
					trace_str = '\n'.join(trace_li[-3:-1])
					con_log(
						f'Error in task: {task["task_name_full"]}\n'
						+ traceback.format_exc()
					)
					if err_counter > s.task_opt_get(
						task['task_function_name']
						, 'err_threshold'
					):
						if sett.developer:
							print(f'err_counter={err_counter}')
						s.task_opt_set(task['task_function_name']
										, 'err_counter', 0)
						msgbox_warning(
							lang.warn_task_error.format(task['task_name_full'])
							+ f':\n{trace_str}'
						)
					else:
						s.task_opt_set(task['task_function_name']
										, 'err_counter', err_counter)
						
			if not s.enabled: return
			if task['single']:
				if task['running']: return
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
		
	def run_scheduler(s):
		time.sleep(0.01)
		local_id = tasks.sched_thread_id
		while (tasks.sched_thread_id == local_id):
			schedule.run_pending()
			time.sleep(1)

	def close(s):
		''' Destructor
			Remove scheduler jobs, hotkey bindings, stop http server
		'''
		if s.http_server:
			s.http_server.shutdown()
			s.http_server.socket.close()
		try:
			keyboard.unhook_all()
		except:
			if sett.developer: print('no hotkeys wih keyboard module')
		if s.global_hk:
			s.global_hk.unregister()
			s.global_hk.stop_listener()
			s.global_hk = None
		schedule.clear()

def create_menu_item(menu, task, func=None, parent_menu=None):
	''' Task - task dict or menu item label
		If task is dict then func = tasks.run_task...
		parent_menu - only for submenu items
	'''
	if type(task) is dict:
		tn = task['task_name']
		if task['hotkey']:
			tn = f"{tn}\t{task['hotkey'].title()}"
		func = lambda evt, temp=task: tasks.run_task(task=temp
													, caller='menu')
	else:
		tn = task
	item = wx.MenuItem(menu, -1, tn)
	if parent_menu:
		parent_menu.Bind(wx.EVT_MENU, func, id=item.GetId())
	else:
		menu.Bind(wx.EVT_MENU, func, id=item.GetId())
	menu.Append(item)

class TaskBarIcon(wx.adv.TaskBarIcon):
	def __init__(s, frame):
		s.frame = frame
		super(TaskBarIcon, s).__init__()
		s.icon = wx.Icon(APP_ICON)
		s.icon_dis = wx.Icon(APP_ICON_DIS)
		s.set_icon()
		s.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, s.on_left_down)

	def CreatePopupMenu(s):
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
		menu.AppendSeparator()
		create_menu_item(menu, lang.menu_edit_crontab, s.on_edit_crontab)
		create_menu_item(menu, lang.menu_reload, load_crontab)
		create_menu_item(menu
			, lang.menu_disable if tasks.enabled else lang.menu_enable
			, s.on_disable
		)
		if sett.developer:
			create_menu_item(menu, 'Show menu 3 sec', s.show_menu_wait)
			create_menu_item(menu, lang.menu_restart, s.on_restart)
			create_menu_item(menu, lang.menu_edit_settings, s.on_edit_settings)
		create_menu_item(menu, lang.menu_exit, s.on_exit)
		return menu

	def set_icon(s, dis:bool=False):
		s.SetIcon(s.icon_dis if dis else s.icon, APP_FULLNAME)

	def show_menu_wait(s, event=None):
		print('show_menu 3 sec')
		s.frame.Raise()
		s.frame.SetFocus()
		
		menu = s.CreatePopupMenu()
		print(s.frame.PopupMenu(menu, pos=(0, 0)))
		menu.Destroy()

	def on_left_down(s, event=None):
		''' Default action on left click to tray icon
		'''
		if app.app_hwnd:
			if sett.hide_console:
				if window_is_visible(app.app_hwnd):
					window_hide(app.app_hwnd)
				else:
					window_show(app.app_hwnd)
			else:
				win32gui.ShowWindow(app.app_hwnd, win32con.SW_RESTORE)
				win32gui.SetForegroundWindow(app.app_hwnd)
			
			

	def on_exit(s, event=None):
		con_log(lang.menu_exit)
		tasks.close()
		wx.CallAfter(s.Destroy)
		s.frame.Close()

	def on_edit_crontab(s, event=None):
		app_start(sett.editor, 'crontab.py')

	def on_edit_settings(s, event=None):
		app_start(sett.editor, r'settings.ini')

	def on_disable(s, event=None):
		tasks.enabled = not tasks.enabled
		app.enabled = tasks.enabled
		if tasks.enabled:
			set_title(APP_NAME)
			con_log('Enabled')
		else:
			set_title(f'Disabled {APP_NAME}')
			con_log('Disabled')
		s.set_icon(not tasks.enabled)
	
	def on_restart(s, event=None):
		s.on_exit()
		if getattr(sys, 'frozen', False):
			os.startfile(os.getcwd() + '\\' + APP_NAME)
		else:
			file_open(f'{APP_PATH}\\{APP_NAME}.py')

	def popup_menu_hk(s):
		print('tb menu by hotkey')
		app.frame.SetFocus()
		time.sleep(0.1)
		app.frame.PopupMenu(s.CreatePopupMenu())

class App(wx.App):
	def OnInit(s):
		s.enabled = True
		s.frame=wx.Frame(None)
		s.taskbar_icon = TaskBarIcon(s.frame)
		hwnd_list = window_find(APP_NAME)
		if len(hwnd_list) == 1:
			s.app_hwnd = hwnd_list[0]
		elif len(hwnd_list) > 1:
			s.app_hwnd = hwnd_list[0]
			if sett.developer:
				msgbox_warning(
					f'Too many {APP_NAME} windows was found: {len(hwnd_list)}'
				)
		else:
			s.app_hwnd = 0
			if sett.developer:
				msgbox_warning(f'None of {APP_NAME} windows was found')
		return True

	def popup_menu_hk(s):
		print('app menu by hotkey')
		s.frame.SetFocus()
		time.sleep(0.1)
		s.frame.PopupMenu(s.taskbar_icon.CreatePopupMenu())
		



def main():
	global app
	global tasks
	global sett
	global lang
	set_title(APP_NAME)
	try:
		sett = Settings()
	except Exception as e:
		print(f'{lang.load_sett_error}:\n{repr(e)}')
		msgbox_warning(f'{lang.load_sett_error}:\n{repr(e)}')
		return
	lang = Language(sett.language)
	print(f'{APP_NAME} version {APP_VERSION}')
	print(lang.load_homepage)
	print(lang.load_donate + '\n\n')
	if sett.developer: print(f'APP_PATH: {APP_PATH}')
	try:
		app = App(False)
		load_crontab()
		tasks.run_at_startup()
		tasks.run_at_sys_startup()
		if sett.developer: app.taskbar_icon.popup_menu_hk()
		
		app.MainLoop()
	except Exception as e:
		trace_li = traceback.format_exc().splitlines()
		trace_str = '\n'.join(trace_li[-3:])
		msg = f'\nGeneral exception:\n\n{repr(e)}\n\n{trace_str}'
		print(msg)
		msgbox_warning(msg)
		input('Press Enter to exit...')
	except KeyboardInterrupt:
		print('Interrupted by keyboard')
		time.sleep(2)


if __name__ == '__main__': main()
