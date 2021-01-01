import sys

_DEF_LANGUAGE = 'en'
class Language:
	def __init__(s, language: str = _DEF_LANGUAGE):
		s.button_close = 'Close'
		s.button_cancel = 'Cancel'
		s.menu_exit = 'Exit'
		s.load_crontab = 'Load crontab from folder'
		s.load_homepage = 'Homepage: https://github.com/vikilpet/Taskopy'
		s.load_donate = 'Donate if you like it: https://www.paypal.me/vikil'
		s.menu_edit_crontab = 'Edit crontab'
		s.menu_reload = 'Reload crontab'
		s.menu_disable = 'Disable'
		s.menu_enable = 'Enable'
		s.menu_restart = 'Restart'
		s.menu_list_run_tasks = 'List of running tasks'
		s.menu_edit_settings = 'Edit settings'
		s.menu_command = 'Enter a command'
		s.menu_command_con = 'Enter a command'
		s.menu_exit = 'Exit'
		s.warn_crontab_reload = 'Failed to reload crontab'
		s.warn_hotkey = 'Wrong hotkey syntax in task «{}»'
		s.warn_schedule = 'Wrong schedule syntax in task «{}»'
		s.warn_task_error = 'Error when executing a task «{}»'
		s.warn_left_click = 'Attempt to bind more than one task to left click: {}'
		s.warn_runn_tasks_con = 'Running tasks'
		s.warn_runn_tasks_msg = 'Some tasks ({}) are being performed now. Close anyway?'
		s.warn_date_format = 'Wrong date format in task «{}»: {}'
		s.warn_event_format = 'Wrong event specification in task «{}»'
		s.warn_too_many_win = 'Too many {} windows was found: {}'
		s.button_close = 'Close'
		s.button_cancel = 'Cancel'
		s.warn_no_run_tasks = 'No running tasks'

		if not (di_str := getattr(
			sys.modules[__name__]
			, '_dict_' + language
			, None
		)):
			if language != _DEF_LANGUAGE:
				print(f'Dictionary for language {language} not found')
			return
		new_trans = set()
		for line in di_str.split('\n'):
			if not line or not '=' in line: continue
			item, trans = line.split('=')
			item = item.strip(); trans = trans.strip()
			if s.__dict__.get(item, None):
				s.__dict__[item] = trans
				new_trans.add(trans)
			else:
				print(f'Unknown item «{item}» in «{language}» language')
		missed = [
			i for i,t in s.__dict__.items()
			if not t in new_trans
		]
		if missed:
			print('No translation for this items:'
			, *missed, sep='\n')
	
	def __getattr__(s, name):
		return 'Language: unknown phrase — «{name}»'

_dict_ru='''
load_crontab=Загрузка кронтаба из папки
load_homepage=Домашняя страница: https://vikilpet.wordpress.com/taskopy/
load_donate=Благодарю за использование.
menu_edit_crontab=Редактировать кронтаб
menu_reload=Перечитать кронтаб
menu_disable=Выключить
menu_enable=Включить
menu_restart=Перезапустить
menu_edit_settings=Редактировать настройки
menu_exit=Выход
menu_command=Ввести команду
menu_command_con=Введите команду
menu_list_run_tasks=Список работающих задач
warn_no_run_tasks=Нет работающих задач
warn_crontab_reload=Не удалось перезагрузить кронтаб
warn_hotkey=Неправильный формат горячей клавиши в задаче «{}»
warn_schedule=Неправильный формат планировщика в задаче «{}»
warn_task_error=Ошибка при выполнении задачи «{}»
warn_left_click=Попытка привязать левому клику больше одной задачи: {}
warn_runn_tasks_con=Работающие задачи
warn_runn_tasks_msg=Некоторые задачи ({} шт.) выполняются в текущий момент. Всё равно закрыть?
warn_date_format=Неправильный формат даты в задаче «{}»: {}
warn_event_format=Неправильный формат события в задаче «{}»
warn_too_many_win=Открыто слишком много окон {}: {}
button_close=Закрыть
button_cancel=Отмена
'''
