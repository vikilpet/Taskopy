import sys

_DEF_LANGUAGE = 'en'
class Language:
	def __init__(self, language: str = _DEF_LANGUAGE):
		self.button_close = 'Close'
		self.button_cancel = 'Cancel'
		self.menu_exit = 'Exit'
		self.load_crontab = 'Load crontab from folder'
		self.load_homepage = 'Homepage: https://github.com/vikilpet/Taskopy'
		self.load_donate = 'Donate if you like it: https://www.paypal.me/vikil'
		self.menu_edit_crontab = 'Edit crontab'
		self.menu_reload = 'Reload crontab'
		self.menu_disable = 'Disable'
		self.menu_enable = 'Enable'
		self.menu_restart = 'Restart'
		self.menu_list_run_tasks = 'List of running tasks'
		self.menu_edit_settings = 'Edit settings'
		self.menu_command = 'Enter a command'
		self.menu_command_con = 'Enter a command'
		self.menu_exit = 'Exit'
		self.warn_crontab_reload = 'Error when reloading the crontab:'
		self.warn_mod_reload = 'Failed to reload module «{}»'
		self.warn_hotkey = 'Wrong hotkey syntax in task «{}»'
		self.warn_schedule = 'Wrong schedule syntax in task «{}»'
		self.warn_every = 'Wrong time syntax in task «{}»: «{}»'
		self.warn_task_error = 'Exception when executing the task «{}»:'
		self.warn_left_click = 'Attempt to bind more than one task to left click: {}'
		self.warn_runn_tasks_con = 'Running tasks'
		self.warn_runn_tasks_msg = 'Some tasks ({}) are being performed now. Close anyway?'
		self.warn_date_format = 'Wrong date format in task «{}»: «{}»'
		self.warn_event_format = 'Wrong event specification in task «{}»'
		self.warn_too_many_win = 'Too many {} windows was found: {}'
		self.button_close = 'Close'
		self.button_cancel = 'Cancel'
		self.warn_no_run_tasks = 'No running tasks'
		self.warn_on_exit = 'Waiting for tasks to complete on exit'
		self.warn_rule_exc = 'Exception in a rule in the task «{}»: {}'

		if not (di_str := getattr(
			sys.modules[__name__]
			, '_dict_' + language
			, None
		)):
			if language != _DEF_LANGUAGE:
				print(f'Dictionary for language {language} not found')
			return
		new_trans = set()
		for line in di_str.splitlines():
			if (not line) or (not '=' in line): continue
			item, trans = line.split('=')
			item = item.strip(); trans = trans.strip()
			if self.__dict__.get(item, None):
				self.__dict__[item] = trans
				new_trans.add(trans)
			else:
				print(f'Unknown item «{item}» in «{language}» language')
		missed = tuple(
			i for i,t in self.__dict__.items()
			if not t in new_trans
		)
		if missed:
			print('No translation for this items:'
			, *missed, sep='\n')
	
	def __getattr__(self, name):
		return f'Language: unknown phrase — «{name}»'

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
warn_crontab_reload=Ошибка при перезагрузке кронтаба:
warn_mod_reload=Не удалось загрузить модуль «{}»
warn_hotkey=Неправильный формат горячей клавиши в задаче «{}»
warn_schedule=Неправильный формат планировщика в задаче «{}»
warn_every=Неправильный формат времени в задаче «{}»: «{}»
warn_task_error=Исключение при выполнении задачи «{}»
warn_left_click=Попытка привязать левому клику больше одной задачи: {}
warn_runn_tasks_con=Работающие задачи
warn_runn_tasks_msg=Некоторые задачи ({} шт.) выполняются в текущий момент. Всё равно закрыть?
warn_date_format=Неправильный формат даты в задаче «{}»: «{}»
warn_event_format=Неправильный формат события в задаче «{}»
warn_too_many_win=Открыто слишком много окон {}: {}
button_close=Закрыть
button_cancel=Отмена
warn_on_exit=Ожидаем завершения задач при выходе
warn_rule_exc=Исключение в правиле у задачи «{}»: {}
'''
