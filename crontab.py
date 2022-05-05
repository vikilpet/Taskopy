from plugins.tools import *
from plugins.plugin_process import *
from plugins.plugin_filesystem import *
from plugins.plugin_network import *
from plugins.plugin_system import *
from plugins.plugin_routeros import *
from plugins.plugin_hotkey import *
from plugins.plugin_mail import *
from plugins.plugin_crypt import *

# Crontab extension:
from ext_embedded import *

# Task with only one parameter - run at application start
# You can deactivate it with the parameter «active=False» like that:
# def demo_task_1(startup=True, active=False):
# or just delete it :-)
def demo__task_1(startup=True):
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

# Example of an HTTP task. «result» option means that the task must
# return some value.
# Open in your browser http://127.0.0.1:8275/demo_task_3
def demo_task_3(http=True, result=True, menu=False):
	# Get a list of files and folders in application directory
	# and return as a br-tag separated string:
	return tcon.HTML_MINI.format(
		'<br>'.join( dir_files('.', subdirs=False) )
	)

def embedded__update(caller:str
, schedule='every().sunday.at("15:30")'):
	emb_app_update(caller=caller)

def embedded__backup_and_purge(schedule='every().day.at("21:30")'):
	emb_backup_and_purge()
