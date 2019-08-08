from plugins.tools import *
from plugins.plugin_process import *
from plugins.plugin_filesystem import *
from plugins.plugin_network import *
from plugins.plugin_winamp import *
from plugins.plugin_system import *
from plugins.plugin_routeros import *

# Task with only one option: run at taskopy startup.
# You can disable it with option «active=False» like that:
# def demo_task_1(startup=True, active=False):
# or just delete it :-)
def demo_task_1(startup=True):
	# Here we will place task actions.

	# Show message box:
	# «+» is for a string concatenation.
	# «\n» is for a new line.
	msgbox(
		'Welkome to Cronolopy!'
		+ '\nI am a demo_task_1.'
		+ '\nWhen you press OK I will open crontab in notepad'
		+ ' so you can disable or delete me.'
	)
	# Open crontab in notepad
	app_start('notepad.exe crontab.py')

# Another example — task with two options: scheduled task
# that is hidden in menu because there is no point to start
# it manually:
def demo_task_2(
	schedule='every().day.at("10:30")'
	, menu=False
):
	# Show message box with exclamation icon:
	msgbox('Take your pills', ui=MB_ICONEXCLAMATION)

# Example of http task. «result» option means that task should
# return some value.
# Open in your browser http://127.0.0.1/task?demo_task_3
def demo_task_3(http=True, result=True):
	# Get list of files and folders in taskopy folder:
	listing = dir_list(r'*')
	# return this list as string divided by html <br> tag:
	return '<br>'.join(listing)

# Запускаем калькулятор и меняем его заголовок на курс продажи
# доллара в Сбербанке. Назначаем выполнение задачи на клик
# левой клавишей мыши по иконке:
def demo_task_4(left_click=True):
	# Запускаем калькулятор:
	app_start(r'calc.exe')
	# Скачиваем json по которому грузится список валют
	# и получаем из него курс продажи доллара:
	usd = json_element(
		'https://www.sberbank.ru/portalserver/proxy/?pipe=shortCachePipe&url=http://localhost/rates-web/rateService/rate/current%3FregionId%3D77%26currencyCode%3D840%26currencyCode%3D978%26rateCategory%3Dbeznal'
		, ['beznal', '840', '0', 'sellValue']
	)
	# Теперь меняем заголовок калькулятора на USD={найденное значение}
	window_title_set('Калькулятор', f'USD={usd}')

# Useful task for backuping crontab and cleaning log and backup folders.
# It is better to not delete this task :-)
def backup_and_purge(
	# Task name «for humans»:
	task_name='Backup and purge'
	# Schedule:
	, schedule='every().day.at("21:30")'
):
	# Backup crontab file to backup folder:
	file_backup('crontab.py', 'backup')
	# Delete backups older than 10 days:
	purge_old('backup', days=10)
	# Delete logs older than 10 days
	purge_old('log', days=10)

# Check github for new version
def taskopy_update(schedule='every().sunday.at("15:30")', submenu='Rare'):
	new_ver = html_element(
		'https://github.com/vikilpet/Taskopy/releases'
		, {'name':'div', 'class':'f1'}
	)[1:-1]	# remove first and last \n
	cur_ver = var_get('taskopy_version')
	if cur_ver == '':
		# It is a first time, don't bother user:
		print('First check for updates')
		# just save current version and exit:
		var_set('taskopy_version', APP_VERSION)
		return
	if cur_ver != new_ver:
		news = html_element(
			'https://github.com/vikilpet/Taskopy/releases'
			, {'name':'div', 'class':'markdown-body'}
		)[1:-1]
		print(f'New version of Taskopy: {new_ver}')
		if msgbox(
			f'New version of Taskopy: {new_ver}\n{news}'
			, dis_timeout=1
			, ui=MB_YESNO + MB_ICONINFORMATION
		) == IDYES:
			var_set('taskopy_version', new_ver)
			file_open('https://github.com/vikilpet/Taskopy/releases')
