from plugins.plugin_network import *
from plugins.plugin_filesystem import *
from plugins.plugin_process import *
from plugins.plugin_system import *
def emb_backup_and_purge():
	for fpath in dir_files(app_dir(), in_ext='py', subdirs=False):
		tprint(file_backup(fpath, 'backup'))
	dir_purge('log', days=10)
	dir_purge('backup', days=20)
def emb_app_update(caller:str):
	VARNAME = '_taskopy_version'
	DST_DIR = temp_dir()
	json_str = http_req('https://api.github.com/repos/vikilpet/Taskopy/releases')
	new_ver = json_element(json_str, element=[0, 'name'])
	cur_ver = var_get(VARNAME)
	if cur_ver == None:
		tprint('first update check')
		var_set(VARNAME, new_ver)
		return
	if cur_ver == new_ver:
		if caller == tcon.CALLER_MENU:
			dialog('No new version', timeout=1)
		return
	news = json_element(json_str, (0, 'body'))
	tprint(f'New version of the Taskopy: {new_ver}\n{news}')
	choice = dialog(
		f'New version of the Taskopy: {new_ver}'
			+ '\n\n' + news.replace('**', '')
		, buttons={
			'Open GitHub page': 'gh'
			, 'Download exe': 'exe'
			, 'Download source': 'src'
			, 'Cancel': 'cancel'
		}
	)
	if choice in (tcon.DL_CANCEL, 'cancel'): return
	var_set(VARNAME, new_ver)
	if choice == 'gh':
		file_open('https://github.com/vikilpet/Taskopy/releases')
		return
	if choice == 'exe':
		url = json_element(json_str, [0, 'assets', 0, 'browser_download_url'])
	else:
		url = json_element(json_str, [0, 'zipball_url'])
	status, data = safe(file_download)(url, destination=DST_DIR)
	if not status:
		dialog(f'Download error:\n{data}')
		return
	if dialog(f'Download finished ({file_size_str(data)})'
	, ('OK','Open archive') ) == 1001:
		file_open(data)

if __name__ != '__main__': patch_import()