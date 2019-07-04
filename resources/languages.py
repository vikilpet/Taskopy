﻿import sys

class Language():
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

_dict_en='''\
load_crontab=Load crontab from folder
load_sett_error=Settings loading error
load_homepage=Homepage: http://github.com/vikilpet
load_donate=Donate: https://www.paypal.me/vikil
menu_edit_crontab=Edit crontab
menu_reload=Reload crontab
menu_disable=Disable
menu_enable=Enable
menu_restart=Restart
menu_edit_settings=Edit settings
menu_exit=Exit
warn_crontab_reload=Failed to reload crontab
warn_hotkey=Wrong hotkey syntax in task «{}»
warn_schedule=Wrong schedule syntax in task «{}»
warn_task_error=Error when executing a task «{}»
'''

_dict_ru='''\
load_crontab=Загрузка кронтаба из папки
load_sett_error=Ошибка загрузки настроек
load_homepage=Домашняя страница: http://vikilpet.wordpress.com/
load_donate=Пожертвования: https://www.paypal.me/vikil
menu_edit_crontab=Редактировать кронтаб
menu_reload=Перечитать кронтаб
menu_disable=Выключить
menu_enable=Включить
menu_restart=Перезапустить
menu_edit_settings=Редактировать настройки
menu_exit=Выход
warn_crontab_reload=Ошибка при загрузке кронтаба
warn_hotkey=Неправильный формат горячей клавиши в задаче «{}»
warn_schedule=Неправильный формат планировщика в задаче «{}»
warn_task_error=Ошибка при выполнении задачи «{}»
'''
