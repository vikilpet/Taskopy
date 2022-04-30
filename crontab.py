from plugins.tools import *
from plugins.plugin_process import *
from plugins.plugin_filesystem import *
from plugins.plugin_network import *
from plugins.plugin_system import *
from plugins.plugin_routeros import *
from plugins.plugin_hotkey import *
from plugins.plugin_mail import *
from plugins.plugin_crypt import *

# Task with only one parameter - run at application start
# You can deactivate it with the parameter «active=False» like that:
# def demo_task_1(startup=True, active=False):
# or just delete it :-)
def demo_task_1(startup=True, submenu='demo'):
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
# Open in your browser http://127.0.0.1:8275/demo_task_3
def demo_task_3(http=True, result=True, menu=False):
	# Get a list of files and folders in application directory:
	listing = dir_list(r'*')
	# return this list as a br-tag separated string:
	return '<br>'.join(listing)

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

# 2021.10.23
# Check to see if there's a new version available
def taskopy_update(
	schedule='every().sunday.at("15:30")'
	, submenu='demo'
):
	VAR = 'taskopy version'
	DOWNLOAD_DIR = temp_dir()
	json_str = http_req('https://api.github.com/repos/vikilpet/Taskopy/releases')
	new_ver = json_element(json_str, element=[0, 'name'])
	cur_ver = dvar_get(VAR)
	if cur_ver == None:
		# The task has been launched for the first time, 
		# do not disturb the user:
		tprint('First update check')
		# Just save the current version and exit:
		dvar_set(VAR, new_ver)
		return
	if cur_ver == new_ver: return
	news = json_element(json_str, [0, 'body'])
	tprint(f'New version of the Taskopy: {new_ver}\n{news}')
	choice = dialog(
		f'New version of the Taskopy: {new_ver}'
		, content=news.replace('**', '')
		, buttons=[
			'Open GitHub page'
			, 'Download exe'
			, 'Download source'
			, 'Cancel'
		]
	)
	# Escape or 'Cancel':
	if choice in (tcon.DL_CANCEL, 1003): return
	# Save the new version:
	dvar_set(VAR, new_ver)
	if choice == 1000:
		# Open page in default browser:
		file_open('https://github.com/vikilpet/Taskopy/releases')
		return
	if choice == 1001:
		# Archive with exe
		url = json_element(json_str, [0, 'assets', 0, 'browser_download_url'])
	else:
		# Archive with code
		url = json_element(json_str, [0, 'zipball_url'])
	status, data = safe(file_download)(url, destination=DOWNLOAD_DIR)
	if not status:
		dialog(f'Download error:\n{data}')
		return
	if dialog(f'Download finished ({file_size_str(data)})'
	, ['OK','Open archive']) == 1001:
		file_open(data)
