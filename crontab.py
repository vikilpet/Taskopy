from plugins.tools import *
from plugins.plugin_process import *
from plugins.plugin_filesystem import *
from plugins.plugin_network import *
from plugins.plugin_winamp import *
from plugins.plugin_system import *
from plugins.plugin_routeros import *
from plugins.plugin_hotkey import *
from plugins.plugin_mail import *
from plugins.plugin_crypt import *

# Task with only one parameter - run at application start
# You can deactivate it with the parameter «active=False» like that:
# def demo_task_1(startup=True, active=False):
# or just delete it :-)
def demo_task_1(startup=True):
	# This is where we'll place the actions

	# Show message
	# «+» is for strings concatenation.
	# «\n» is for a new line.
	dialog(
		'Welkome to Taskopy!'
		+ '\nI am demo_task_1.'
		+ '\nWhen you press OK I will open the crontab in notepad'
		+ ' so you can disable or even delete me.'
	)
	app_start('notepad.exe', 'crontab.py')

# Another example — task with two options: scheduled task
# that is hidden in the menu because there is no point in
# launching it manually:
def demo_task_2(schedule='every().day.at("10:30")', menu=False):
	# Show message box with exclamation point icon:
	dialog('Take your pills!')

# Example of an HTTP task. «result» option means that the task should
# return some value.
# Open in your browser http://127.0.0.1/task?demo_task_3
def demo_task_3(http=True, result=True):
	# Get a list of files and folders in application directory:
	listing = dir_list(r'*')
	# return this list as a br-tag separated string:
	return '<br>'.join(listing)

# Запускаем калькулятор и меняем его заголовок на курс продажи
# доллара в Сбербанке. Назначаем выполнение задачи на клик
# левой клавишей мыши по иконке:
def demo_task_4(left_click=True):
	# Запускаем калькулятор:
	app_start(r'calc.exe')
	# Скачиваем json по которому грузится список валют
	# и получаем из него курс продажи доллара
	usd = json_element(
		'https://www.sberbank.ru/portalserver/proxy/?pipe=shortCachePipe&url=http://localhost/rates-web/rateService/rate/current%3FregionId%3D77%26currencyCode%3D840%26currencyCode%3D978%26rateCategory%3Dbeznal'
		# Обратите внимание: в их данных числовые значения присутствуют в виде строк:
		, ['beznal', '840', '0', 'sellValue']
	)
	# Теперь меняем заголовок калькулятора на USD={найденное значение}
	window_title_set('Калькулятор', f'USD={usd}')

def backup_and_purge(
	# Task name «for humans»:
	task_name='Backup and purge'
	, schedule='every().day.at("21:30")'
):
	# Backup crontab file to backup folder:
	file_backup('crontab.py', 'backup')
	# Delete backups older than 10 days:
	dir_purge('backup', days=10)
	# Delete logs older than 10 days
	dir_purge('log', days=10)

# Check to see if there's a new version available
def taskopy_update(schedule='every().sunday.at("15:30")', submenu='Rare'):
	new_ver = html_element(
		'https://github.com/vikilpet/Taskopy/releases'
		, {'name':'div', 'class':'f1'}
	)
	cur_ver = var_get('taskopy_version')
	if cur_ver == '':
		# The task has been launched for the first time, 
		# do not disturb the user:
		tprint('First check for updates')
		# Just save the current version and exit:
		var_set('taskopy_version', new_ver)
		return
	if cur_ver != new_ver:
		news = html_element(
			'https://github.com/vikilpet/Taskopy/releases'
			, {'name':'div', 'class':'markdown-body'}
		)
		tprint(f'New version of the Taskopy: {new_ver}')
		choice = dialog(
			f'New version of the Taskopy: {new_ver}'
			, content=news[:200]
			, buttons=['Open GitHub page', 'OK']
		)
		if choice == 1000:
			# Save the new version:
			var_set('taskopy_version', new_ver)
			# Open page in default browser:
			file_open('https://github.com/vikilpet/Taskopy/releases')
		elif choice == 1001:
			# Just save and do nothing
			var_set('taskopy_version', new_ver)
