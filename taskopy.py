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
from plugins.tools import *
from plugins.plugin_filesystem import *
from plugins.plugin_process import *
from plugins.plugin_http_server import http_server_start
from plugins.plugin_hotkey import GlobalHotKeys
from resources.languages import Language


tasks = None
app = None
crontab = None
settings = None
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

class Settings():
	''' Load global settings from settings.ini
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
				else:
					s.__dict__[setting[0]] = setting[1]
		for setting in APP_SETTINGS:
			s.__dict__.setdefault(setting[0], setting[1])

def load_crontab(event=None)->bool:
	global tasks
	global crontab
	cron_log(f'{lang.load_crontab} {os.getcwd()}')
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
		cron_log(traceback.format_exc())
		msgbox_warning(f'{lang.warn_crontab_reload}:\n\n{trace_str}')
		return False


class Tasks():
	''' Tasks from crontab and they properties '''
	def __init__(s):
		s.enabled = True
		s.task_list = []
		s.task_list_menu = []
		s.task_list_submenus = []
		s.task_list_startup = []
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
				task_opts['task_name'] = item.replace('_'
												, ' ').capitalize()
				task_opts['task_name_full'] = task_opts['task_name']
			if task_opts['schedule']:
				s.add_schedule(task_opts)
			if task_opts['hotkey']: s.add_hotkey(task_opts)
			if task_opts['left_click']:
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
		s.task_list_menu[:] = sorted(s.task_list_menu
			, key=lambda k: k['task_name'].lower()
		)
		for subm in s.task_list_submenus:
			subm[1][:] = sorted(subm[1]
				, key=lambda k: k['task_name'].lower()
			)
		if s.global_hk:
			t = threading.Thread(target=s.global_hk.listen, daemon=True)
			t.start()
			s.global_hk_thread_id = t.ident
		if s.task_list_http:
			threading.Thread(
				target=http_server_start
				, args=(settings, s)
				, daemon=True
			).start()
		t = threading.Thread(target=s.run_scheduler, daemon=True)
		t.start()
		s.sched_thread_id = t.ident
		if settings.developer: print(f'Total tasks: {len(s.task_list)}')
	
	def add_hotkey(s, task):
		def hk_error(error):
			cron_log(error)
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
				cron_log(repr(e))
				msgbox_warning(
					lang.warn_schedule.format(task['task_name_full'])
					+ ':\n' + inter
				)

	def run_at_startup(s):
		for task in s.task_list_startup:
			s.run_task(task, caller='startup')
			
	def run_at_sys_startup(s):
		if win32api.GetTickCount() < (3 * 60 * 1000):
			for task in s.task_list_sys_startup:
				s.run_task(task, caller='sys_startup')
	
	def task_opt_set(s, task_function_name:str, option:str, value):
		''' Set tasks.task_list option
		'''
		for task in s.task_list:
			if task['task_function_name'] == task_function_name:
				task[option] = value
				break

	def run_task(s, task:dict, caller:str=None, data=None):
		''' task - dict with task options
			Logging and other staff
			caller - who actually launched the task.
				It can be 'hotkey', 'menu', 'scheduler', 'http' etc.
				So you can check inside task function who calls
				function this time.
		'''
		def run_task_inner():
			def catcher(result):
				try:
					s.task_opt_set(task['task_function_name'], 'running', True)
					task_kwargs = {}
					if 'caller' in task['task_function'].__code__.co_varnames:
						task_kwargs['caller'] = caller
					if 'data' in task['task_function'].__code__.co_varnames:
						task_kwargs['data'] = data
					r = task['task_function'](**task_kwargs)
					if r: result.append(r)
					s.task_opt_set(task['task_function_name'], 'running', False)
				except Exception as e:
					s.task_opt_set(task['task_function_name'], 'running', False)
					trace_li = traceback.format_exc().splitlines()
					trace_str = '\n'.join(trace_li[-3:])
					cron_log(
						f'Error in task: {task["task_name_full"]}\n'
						+ traceback.format_exc()
					)
					msgbox_warning(
						lang.warn_task_error.format(task['task_name_full'])
						+ f':\n{trace_str}'
					)
			if not s.enabled: return
			if task['single']:
				if task['running']: return
			if task['log']:
				cs = f' ({caller})' if caller else ''
				cron_log(f'task{cs}: {task["task_name_full"]}')
			result = []
			if task['result']:
				t = threading.Thread(target=catcher, args=(result,)
									, daemon=True)
				t.start()
				t.join()
				if result:
					return result[0]
			else:
				threading.Thread(target=catcher, args=(result,)
								, daemon=True).start()
		if task['result']:
			threading.Thread(
				target=run_task_inner
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
			if settings.developer: print('no hotkeys wih keyboard module')
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
		if sys.modules.get('crontab') is not None:
			for task in tasks.task_list_menu:
				create_menu_item(menu, task)
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
		if settings.developer:
			create_menu_item(menu, 'Show menu 3 sec', s.show_menu_wait)
			create_menu_item(menu, lang.menu_restart, s.on_restart)
			create_menu_item(menu, lang.menu_edit_settings, s.on_edit_settings)
		create_menu_item(menu, lang.menu_exit, s.on_exit)
		return menu

	def set_icon(s, dis:bool=False):
		s.SetIcon(s.icon_dis if dis else s.icon, APP_NAME)

	def show_menu_wait(s, event=None):
		print('show_menu 3 sec')
		s.frame.Raise()
		s.frame.SetFocus()
		
		menu = s.CreatePopupMenu()
		print(s.frame.PopupMenu(menu, pos=(0, 0)))
		menu.Destroy()

	def on_left_down(s, event=None):
		print ('Tray icon was left-clicked.')
		menu = s.CreatePopupMenu()
		s.PopupMenu(menu)

	def on_exit(s, event=None):
		cron_log(lang.menu_exit)
		tasks.close()
		wx.CallAfter(s.Destroy)
		s.frame.Close()

	def on_edit_crontab(s, event=None):
		app_start(f'{settings.editor} crontab.py')

	def on_edit_settings(s, event=None):
		app_start(f'{settings.editor} settings.ini')

	def on_disable(s, event=None):
		tasks.enabled = not tasks.enabled
		app.enabled = tasks.enabled
		if tasks.enabled:
			set_title(APP_NAME)
			cron_log('Enabled')
		else:
			set_title(f'Disabled {APP_NAME}')
			cron_log('Disabled')
		s.set_icon(not tasks.enabled)
	
	def on_restart(s, event=None):
		s.on_exit()
		if getattr(sys, 'frozen', False):
			os.startfile(os.getcwd() + '\\' + APP_NAME)
		else:
			app_start(os.getcwd() + f'\\{APP_NAME}.py', minimized=True)

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
		return True

	def popup_menu_hk(s):
		print('app menu by hotkey')
		s.frame.SetFocus()
		time.sleep(0.1)
		s.frame.PopupMenu(s.taskbar_icon.CreatePopupMenu())
		


def main():
	global app
	global tasks
	global settings
	global lang
	set_title(APP_NAME)
	try:
		settings = Settings()
	except Exception as e:
		print(f'{lang.load_sett_error}:\n{repr(e)}')
		msgbox_warning(f'{lang.load_sett_error}:\n{repr(e)}')
		return
	lang = Language(settings.language)
	print(f'{APP_NAME} version {APP_VERSION}')
	print(lang.load_homepage)
	print(lang.load_donate + '\n\n')
	if settings.developer: print(f'APP_PATH: {APP_PATH}')
	try:
		app = App(False)
		load_crontab()
		tasks.run_at_startup()
		tasks.run_at_sys_startup()
		if settings.developer: app.taskbar_icon.popup_menu_hk()
		
		app.MainLoop()
	except Exception as e:
		msg = f'\nGeneral exception: {repr(e)}\n'
		print(msg)
		msgbox_warning(msg + '\nCheck console!')
		input('Press Enter to exit...')
	except KeyboardInterrupt:
		print('Interrupted by keyboard')
		time.sleep(2)


if __name__ == '__main__': main()
