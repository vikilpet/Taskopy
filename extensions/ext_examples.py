'''
Extension with examples of *complex* tasks
'''

from plugins.plugin_process import *
from plugins.plugin_filesystem import *
from plugins.plugin_network import *
from plugins.plugin_system import *
from plugins.plugin_routeros import *
from plugins.plugin_hotkey import *
from plugins.plugin_mail import *
from plugins.plugin_crypt import *

def examp_autoruns(exe_path:str, caller:str
, max_table_width=80):
	'''
	Check if something new has appeared in the system autorun.
	Wrapper for the Sysinternals autoruns:
	https://docs.microsoft.com/en-us/sysinternals/downloads/autoruns  
	*exe_path* - full path to the console version:  
	autorunsc64.exe (note the 'c' near the end)

	Usage example (crontab):

		def examples__autoruns(
			caller:str
			, every='day 17:31'
		):
			examp_autoruns(
				exe_path='d:\\soft\\sysinternals\\autorunsc64.exe'
				, caller=caller
			)

	First you have to run it manually and accept the agreement.

	The autoruns run without elevated privileges
	shows slightly less files. We can't run it automatically in
	elevated mode so lets do it in manual (runas) at least.

	Autoruns command-line options:  
	m — hide Microsoft signed  
	ct — tab-separated export  
	with the -s option it will not show new files with a signature  
	'''
	CMD = (exe_path, '-nobanner', '-ct', '-m', '-a', '*')
	HASH_ALG = 'sha256'
	# It's convient to store name for var_* in a variable:
	VAR_NAME = 'autoruns'
	
	def csv_to_hash_dict(content:str)->dict:
		# Returns dict:
		# {'path/to/exe': 'hash'}
		hashes = {}
		for line in content.splitlines()[1:]:
			if len(line) < 100:
				# last line
				continue
			# full image path is 8 element in line:
			image_path = line.split('\t')[8]
			# there may be empty lines:
			if not image_path: continue
			if not file_exists(image_path):
				# not all paths are available from 32-bit code:
				hashes[image_path] = 'nx-file'
				continue
			try:
				hashes[image_path] = file_hash(image_path, HASH_ALG)
			except:
				hashes[image_path] = 'hash error'
		return hashes
	
	new_out = proc_start(CMD, capture=True, encoding='utf-16')[1]
	prev_out = var_get(VAR_NAME)
	if not prev_out:
		tprint('first run')
		if caller in (tcon.CALLER_LOAD, tcon.CALLER_MENU):
			dialog('First run', timeout=5)
		var_set( VAR_NAME, json.dumps( csv_to_hash_dict(new_out) ) )
		return
	prev_dct = json.loads(prev_out)
	new_dct = csv_to_hash_dict(new_out)
	# Dictionary for changes
	# Format: {'c:\\prog.exe': 'new'}
	changes = {}
	for path, path_hash in new_dct.items():
		if not path in prev_dct:
			# Just a new item:
			changes[path] = 'new'
			continue
		if path_hash != prev_dct.get(path):
			changes[path] = 'changed'
	# Non-existing paths:
	for path in prev_dct:
		if not path in new_dct: changes[path] = 'deleted'
	if not changes:
		# Notify user only if it was started manually.
		if caller in (tcon.CALLER_LOAD, tcon.CALLER_MENU):
			dialog('No change', timeout=2)
		return
	print(f'\nChanges ({len(changes)}):')
	table = []
	for path, status in changes.items():
		table.append((status, path))
	table_print(table, use_headers=('Status', 'File')
	, max_table_width=max_table_width)
	choice = dialog(
		f'Changes from autoruns ({len(changes)}):\n\n'
			+ '\n'.join(
				f'{s}: {p}' for p, s in tuple(changes.items())[0:3]
			)
		, content='More in console' if len(table) > 3 else None
		, buttons={
			'Save and launch autoruns': 'sl'
			, 'Just launch autoruns': 'l'
			, 'Just save': 's'
			, 'Cancel': 'c'
		}
	)
	if choice == 'sl':
		var_set(VAR_NAME, json.dumps(new_dct))
		# 'runas' - run with elevated privileges
		file_open(
			exe_path.replace('autorunsc', 'autoruns')
			, operation='runas'
		)
	elif choice == 'l':
		file_open(
			exe_path.replace('autorunsc', 'autoruns')
			, operation='runas'
		)
	elif choice == 's':
		var_set(VAR_NAME, json.dumps(new_dct))

if __name__ != '__main__': patch_import()