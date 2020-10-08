import sys

class Language:
	def __init__(s, language:str='en'):
		di_str = getattr(
			sys.modules[__name__]
			, '_dict_' + language, _dict_en
		)
		di = dict(v.split('=') for v in di_str[:-1].split('\n'))
		di_def = dict(v.split('=') for v in _dict_en[:-1].split('\n'))
		for i in di_def.items():
			di.setdefault(i[0], i[1])
		s.__dict__.update(di)
	
	def __getattr__(s, name):
		return 'unknown phrase'

_dict_en='''\
load_crontab=Load crontab from folder
load_homepage=Homepage: https://github.com/vikilpet/Taskopy
load_donate=Donate if you like it: https://www.paypal.me/vikil
menu_edit_crontab=Edit crontab
menu_reload=Reload crontab
menu_disable=Disable
menu_enable=Enable
menu_restart=Restart
menu_edit_settings=Edit settings
menu_command=Enter a command
menu_command_con=Enter a command
menu_exit=Exit
warn_crontab_reload=Failed to reload crontab
warn_hotkey=Wrong hotkey syntax in task «{}»
warn_schedule=Wrong schedule syntax in task «{}»
warn_task_error=Error when executing a task «{}»
warn_left_click=Attempt to bind more than one task to left click: {}
warn_runn_tasks_con=Running tasks
warn_runn_tasks_msg=Some tasks ({}) are being performed now. Close anyway?
warn_date_format=Wrong date format in task «{}»: {}
warn_event_format=Wrong event specification in task «{}»
'''

_dict_ru='''\
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
warn_crontab_reload=Ошибка при загрузке кронтаба
warn_hotkey=Неправильный формат горячей клавиши в задаче «{}»
warn_schedule=Неправильный формат планировщика в задаче «{}»
warn_task_error=Ошибка при выполнении задачи «{}»
warn_left_click=Попытка привязать левому клику больше одной задачи: {}
warn_runn_tasks_con=Работающие задачи
warn_runn_tasks_msg=Некоторые задачи ({} шт.) выполняются в текущий момент. Всё равно закрыть?
warn_date_format=Неправильный формат даты в задаче «{}»: {}
warn_event_format=Неправильный формат события в задаче «{}»
'''
