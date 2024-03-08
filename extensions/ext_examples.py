r'''
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

@task_add
def examples__file_encrypt():
	' Choose a file and encrypt it '
	fpath = file_dialog()
	if not fpath: return
	pwd = inputbox('Password:', is_pwd=True)
	if not pwd: return
	status, fullpath = file_encrypt(fpath, pwd)
	if not status:
		tprint(str_indent(fullpath))
		dialog('File encryption error')
		return
	dialog(f'Done:\n{fullpath}')

@task_add
def examples__file_decrypt():
	' Choose a file and decrypt it '
	fpath = file_dialog()
	if not fpath: return
	pwd = inputbox('Password:', is_pwd=True)
	if not pwd: return
	status, fullpath = file_decrypt(fpath, pwd)
	if not status:
		tprint(str_indent(fullpath))
		dialog('File decryption error')
		return
	dialog(f'Done:\n{fullpath}')

def examp_cert_check(caller:str, codepage:str=''
, stores:tuple=('Root', 'AuthRoot')):
	r'''
	Find the difference in the PC certificate list and the similar
	list from Windows Update.

	Links:
	
	- https://justinparrtech.com/JustinParr-Tech/windows-certutil-list-certificate-stores/
	- https://www.computerworld.com/article/3008113/dell-installs-self-signed-root-certificate-on-laptops-endangers-users-privacy.html
	- https://support.microsoft.com/en-us/topic/an-automatic-updater-of-untrusted-certificates-is-available-for-windows-vista-windows-server-2008-windows-7-and-windows-server-2008-r2-117bc163-d9e0-63ad-5a79-e61f38be8b77
	
	'''

	def parser(dump:str)->dict:
		dct = {}
		# There is a difference between a pc and a wu dump
		for sect in dump.split('================'):
			hsh = re_find(sect, r'(?:\):\s)([0-9a-z\s]{32,})')
			if not hsh: continue
			name = re_find(sect, r'(?:\s(?:CN=|OU=|O=))(.+?)[,\r\n]', re_flags=0)
			if caller == tcon.CALLER_MENU:
				if not name: tprint(f'no name: {hsh}')
			dct[hsh[0].strip()] = name[0].strip() if name else '?'
		return dct

	if not codepage: codepage = sys_codepage()
	dump_file = temp_file(suffix=".sst")
	ret, out, _ = proc_start('certutil', f'-generateSSTFromWU {dump_file}'
	, capture=True)
	if ret:
		dialog(f'certutil wu download error: {out}')
		return
	ret, out, _ = proc_start('certutil', dump_file, capture=True)
	if ret:
		dialog(f'certutil wu read error: {out}')
		return
	file_recycle(dump_file)
	hashes_wu = parser(out)
	hashes_pc = {}
	for store in stores:
		ret, out, _ = proc_start('certutil', f'-store {store}'
		, capture=True, encoding=codepage)
		if ret:
			dialog(f'certutil store {store} error: {out}')
			return
		hashes_pc.update(parser(out))
	table = [('Src', 'Name', 'Hash')]
	hashes_pc_only, diff = {}, set()
	for hsh, name in hashes_pc.items():
		if not hsh in hashes_wu:
			hashes_pc_only[hsh] = name
			diff.add(hsh)
			table.append(('pc', name, hsh))
	if caller == tcon.CALLER_MENU or diff:
		tprint(f'{len(hashes_pc)=}, {len(hashes_wu)=}')
		table_print(table, sorting=(0, 1))
	if not set(
		var_get('cert_check_diff', as_literal=True, default=())
	).symmetric_difference(diff):
		if caller == tcon.CALLER_MENU:
			dialog('No new PC-only certificates', timeout='2 sec')
		return
	if len(hashes_pc_only) == 0:
		return
	# Show application window and dialog only if there is a difference:
	app_win_show()
	if dialog('Save the new difference?', ('No', 'Yes')) == 1001:
		var_set('cert_check_diff', diff)

# pip install pytelegrambotapi --upgrade
# This module is not included in the standard set of *exe* distribution
# , comment it out to use:
# import telebot
# Just for a syntax tips:
# from telebot.types import Message
def telegram__tlg_bot_start(
	# Use *every* to ensure that the bot always works
	# , even after a crash/disconnect:
	every='1 sec'
	# We ignore 10 errors so that we don't get messages
	# every second if we make a mistake in the code:
	, err_threshold=10
):
	token = 'YOUR BOT TOKEN FROM BOTFATHER'
	bot = telebot.TeleBot(token)
	# Save the bot for access from other tasks:
	gdic['tlg_bot'] = bot
	
	@bot.message_handler(commands=['start', 'help'])
	def send_welcome(msg:Message):
		# Just send a chat id:
		bot.send_message(msg.chat.id, str(msg.chat.id))

	@bot.message_handler(func=lambda message: True)
	def new_msg(msg:Message):
		# We got a message.
		# Get user name:
		user_str = msg.from_user.first_name
		# Print message:
		tprint(f'{user_str}: {msg.text}')
		if msg.text.lower() == 'hi':
			# a specific response for a known message:
			bot.send_message(msg.chat.id, 'Hello!')
		else:
			# Unknown message:
			bot.reply_to(msg, f"I don't get it 🤔")

	# Start the bot:
	bot.infinity_polling()
	# Signaling that we're out of the infinite server polling loop:
	tprint('exit')

# Use *on_load* so that it stops the bot
# when the crontab is reloaded. This is handy
# while you are changing bot functionality 
# in the *_start* task and you need to restart bot.
# When you're done, this can be turned off.
def telegram__tlg_bot_stop(on_load=True, on_exit=True):
	if bot := gdic.get('tlg_bot'): bot.stop_bot()

if __name__ != '__main__': patch_import()