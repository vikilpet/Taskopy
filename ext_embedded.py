from plugins.plugin_network import *
from plugins.plugin_filesystem import *
from plugins.plugin_process import *
from plugins.plugin_system import *

# This is the crontab extension

# 2024.01.03 abs path
def emb_backup_and_purge(log_days:int=30, backup_days:int=30):
	' Make backup of crontab and extensions to the *backup* directory '
	for fpath in dir_files(app_dir(), in_ext='py', subdirs=False):
		tprint(file_backup(fpath, 'backup'))
	# Delete logs older than 10 days:
	dir_purge( (app_dir(), 'log'), days=log_days)
	# Delete backups older than 20 days:
	dir_purge( (app_dir(), 'backup'), days=backup_days)

# 2024.01.03 abs path
def emb_app_update(caller:str):
	' Check to see if there is a new version available '
	VARNAME = '_taskopy_version'
	DST_DIR = temp_dir()
	json_str = http_req('https://api.github.com/repos/vikilpet/Taskopy/releases')
	new_ver = json_element(json_str, element=[0, 'name'])
	cur_ver = var_get(VARNAME)
	if cur_ver == None:
		# The task has been launched for the first time, 
		# do not disturb the user:
		tprint('first update check')
		# Just save the current version and exit:
		var_set(VARNAME, new_ver)
		return
	if cur_ver == new_ver:
		# Show dialog only if the taks was started manually:
		if caller == tcon.CALLER_MENU:
			dialog('No new version', timeout=1)
		return
	news = json_element(json_str, (0, 'body'))
	tprint(f'new version of the Taskopy: {new_ver}\n{news}')
	choice = dialog(
		f'New version of the Taskopy: {new_ver}'
			+ '\n\n' + news.replace('*', '')
		, buttons={
			'Open GitHub page': 'github'
			, 'Download exe': 'exe'
			, 'Download source': 'src'
			, 'Skip this version': 'skip'
			, 'Cancel': 'cancel'
		}
	)
	# *Escape* key goes here too:
	if choice in (tcon.DL_CANCEL, 'cancel'): return
	# Save the new version:
	var_set(VARNAME, new_ver)
	if choice == 'skip':
		return
	elif choice == 'github':
		# Open page in default browser:
		file_open('https://github.com/vikilpet/Taskopy/releases')
		return
	if choice == 'exe':
		# Archive with exe
		url = json_element(json_str, [0, 'assets', 0, 'browser_download_url'])
	else:
		# Archive with code
		url = json_element(json_str, [0, 'zipball_url'])
	status, data = safe(file_download)(url, destination=DST_DIR)
	if not status:
		dialog(f'Download error:\n{data}')
		return
	# Show a dialog with the size of the downloaded file:
	if dialog(f'Download finished ({file_size_str(data)})'
	, {'OK': '', 'Open archive': 'open'} ) == 'open':
		file_open(data)

# 2024.01.03 abs path
@task_add
def embedded__add_to_startup(caller=''):
	' Add the program to the startup '
	shortcut_create(
		# The program can be in the form of an exe or a script file:
		(app_dir(), 'taskopy.exe' if is_app_exe() else 'taskopy.py')
		# Destination - the startup directory of a user:
		, dest=(dir_user_startup(), 'taskopy.lnk')
		# The program must be run from its directory:
		, cwd=app_dir()
		# It's a nice to have an icon:
		, icon_fullpath=(app_dir(), APP_ICON_ICO)
		# Run minimized:
		, win_style=win32con.SW_SHOWMINNOACTIVE
	)

@task_add
def embedded__Create_AppID(appid:str=APP_NAME, appname:str=APP_NAME
, icon:str='app'):
	r'''
	Adds the *AppID* to the registry for use with `toast` notifications.  
	*icon* - an *.ico* file.  
	What it's for:  
	
	1. So that the toast has an icon.
	2. To make the `on_click` action work when clicking in *Action center*.  

	'''
	KEY_ROOT = 'HKEY_CURRENT_USER\\SOFTWARE\\Classes\\AppUserModelId\\'
	if icon == 'app': icon = path_get((app_dir(), APP_ICON_ICO))
	if icon:
		assert file_exists(icon), 'Icon file does not exist'
		assert file_ext(icon) == 'ico', 'Icon file must be of type .ico'
	key_path = KEY_ROOT + appid
	res = registry_path_add(key_path)
	if res != True:
		dialog(f'Path fail: {res}')
		return
	res = registry_set(f'{key_path}\\DisplayName', value=appname
	, value_type=winreg.REG_SZ)
	if res != True:
		dialog(f'DisplayName fail: {res}')
		return
	if not icon: return
	res = registry_set( f'{key_path}\\IconUri', value=icon
	, value_type=winreg.REG_SZ)
	if res != True:
		dialog(f'IconUri fail: {res}')
		return
	toast('Done!')

	

if __name__ != '__main__': patch_import()