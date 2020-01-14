# Taskopy
### Platform for running Python-based scripts on Windows with hotkeys, tray menu, HTTP server and many more.

<p align="center">
	<img src="https://i6.imageban.ru/out/2019/07/04/a6f6538a80bc7a62ab06ce5cea295a93.png">
</p>
<!---
2020.01.05 22:26:08
-->
Run your python code with hotkey or by HTTP-request just like that:

	def my_task(hotkey='ctrl+shift+t', http=True):
		print('This is my code!')

Then press Ctrl+Shift+T or open in browser URL http://127.0.0.1:8275/task?my_task and your task will be executed.

Another example: show message box every day at 10:30 and hide this task from menu:

	def my_another_task(schedule='every().day.at("10:30")', menu=False):
		msgbox('Take the pills', ui=MB_ICONEXCLAMATION)

## Contents
- [Installation](#installation)
- [Usage](#usage)
- [Task Options](#task-options)
- [Settings](#settings)
- [Keywords](#keywords)
	- [Miscelanneous](#miscelanneous)
	- [Keyboard](#keyboard)
	- [Filesystem](#filesystem)
	- [Network](#network)
	- [System](#system)
	- [Mail](#mail)
	- [Process](#process)
	- [Cryptography](#cryptography)
	- [Mikrotik RouterOS](#mikrotik-routeros)
	- [Winamp](#winamp)
- [Firefox extension](#firefox-extension)
- [Context menu](#context-menu)
- [Help Me](#help-me)
- [Task Examples](#task-examples)

## Installation
### Option 1: binary file

**Requirements:** Windows 7 and above.
You can [download](https://github.com/vikilpet/Taskopy/releases) archive with binary release but many of lousy antiviruses don't like python inside EXE so VirusTotal shows about 7 detects.

### Option 2: Python
**Requirements:** Python 3.7.4; Windows 7 and above.

Download project, install requirements:

	pip install -r requirements.txt

Make shortcut to taskopy.py in Startup folder:

	%userprofile%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\

In shortcut options choose *Run: minimized* option and change shortcut icon to resources\logo.ico

## Usage
Open crontab.py in your favorite text editor and create your task as function with arguments:

	def demo_task_3('left_click'=True, log=False):
		app_start('calc.exe')

Then right click on tray icon and choose "Reload crontab" and your task is ready.

## Task options
This is what you need to put in round brackets in task (function). It is not actual arguments for function.

Format: **option name** (default value) — description.

- **task_name** (None) — name for humans.
- **menu** (True) — show in tray menu.
- **hotkey** (None) — assign to global hotkey. Example: *hotkey='alt+ctrl+m'*
- **hotkey_suppress** (True) — if set to False hotkey will not supressed so active window ill still receive it.
- **schedule** (None) — add to schedule. Functionality provided by [schedule project](https://github.com/dbader/schedule) so you better refer to their [documentation](https://schedule.readthedocs.io/en/stable/).
	Run task every hour:

		schedule='every().hour'

	Run task every wednesday at 13:15:

		schedule='every().wednesday.at("13:15")'

	You can set multiple schedule at once with list:

		schedule=['every().wednesday.at("18:00")', 'every().friday.at("17:00")']

- **active** (True) — to enable-disable task.
- **startup** (False) — run at taskopy startup.
- **sys_startup** (False) — run at Windows startup (uptime is less than 3 min).
- **left_click** (False) — assign to mouse left button click on tray icon.
- **log** (True) — log to console and file.
- **single** (True) — allow only one instance of running task.
- **submenu** (None) — place task in this sub menu.
- **result** (False) — task should return some value. Use together with http option to get page with task results.
- **http** (False) — run task by HTTP request. HTTP request syntax: http://127.0.0.1:8275/task?your_task_name where «your_task_name» is the name of function from crontab.
	If option **result** also enabled then HTTP request will show what task will return or 'OK' if there is no value returned.
	Example:

		def demo_task_4(http=True, result=True):
			# Get list of files and folders in Taskopy folder:
			listing = dir_list('*')
			# return this list as string divided by html br tag:
			return '<br>'.join(listing)

	Result in browser:

		backup
		crontab.py
		log
		resources
		settings.ini
		taskopy.exe

	See also [settings](#settings) section for IP and port bindings.
- **http_dir** - folder where to save files sent via HTTP POST request. If not set then use system temporary folder.
- **caller** - place this option before other options and in task body you will know who actually launched task this time. Possible values: http, menu, scheduler, hotkey. See *def check_free_space* in [Task Examples](#task-examples).
- **data** - use together with **http** and place this option before other options and it will filled with HTTP request data and you will able to work with them in task body.
	*data.client_ip* — IP-address of request.
	*data.path* — full relative path of request including */task?*
	*data.post_file* - full path to the received file, which was sent to the task via POST request (see **page_get**).
	*data* will contain all HTTP-request headers such as *User-Agent*, 	*Accept-Language* etc.
	If you will construst request URL with common scheme *&param1=value1&param2=value2* they will be processed and added to data and you can access them in task body as data.param1, data.param2. Example:

		def alert(data, http=True, single=False, menu=False):
			msgbox(
				data.text
				# Use data.title if possible otherwise just use 'Alert' as message title.
				, title=data.title if data.title else 'Alert'
				, dis_timeout=1
			)

	Type in address bar of browser something like this:
	http://127.0.0.1:8275/task?alert&text=MyMsg&title=MyTitle
	and you will see messagebox with title and text from URL.
- **idle** - Perform the task when the user is idle for the specified time. For example, *idle='5 min'* - run when the user is idle for 5 minutes. The task is executed only once during the inactivity.
- **err_threshold** - do not report any errors in the task until this threshold is exceeded.

## Settings
Global settings are stored in *settiings.ini* file.

Format: **setting** (default value) — description.

- **language** (en) — menu and msgbox language. Variants: en, ru.
- **editor** (notepad) — text editor for «Edit crontab» menu command.
- **hide_console** - hide the console window.
- **server_ip** (127.0.0.1) — bind HTTP server to this local IP. For access from any address set to *0.0.0.0*.
	**IT IS DANGEROUS TO ALLOW ACCESS FROM ANY IP!** Do not use *0.0.0.0* in public networks or limit access with firewall.
- **white_list** (127.0.0.1) — a list of IP addresses separated by commas from which requests are received.
- **server_port** (8275) — HTTP server port.

## Keywords
### Miscelanneous
- **balloon(msg:str, title:str=APP_NAME,timeout:int=None, icon:str=None)** - shows *baloon* message from tray icon. `title` - 63 symbols max, `msg` - 255 symbols. `icon` - 'info', 'warning' or 'error'.
- **jobs_batch(func_list:list, timeout:int)->list**: — Runs functions (they may not be same) in threads and waits when all of them return result or timeout is expired. *func_list* - list of sublist, where sublist should consist of 3 items: function, (args), {kwargs}. Returns list of *job* objects, where *job* have these attributes: function, args, kwargs, result, time. Example:

		func_list = [
			[function1, (1, 3, 4), {'par1': 2, 'par2':3}]
			, [function2, (), {'par1':'foo', 'par2':'bar'}]
			...
		]
		jobs:
		[
			<job.func=function1, job.args = (1, 3, 4), job.kwargs={'par1': 2, 'par2':3}
				, job.result=True, job.time='0:00:00.0181'>
			, <job.func=function2, job.args = (), job.kwargs={'par1':'foo', 'par2':'bar'}
				, job.result=[True, data], job.time='0:00:05.827'>

			...
		]
- **jobs_pool(function:str, pool_size:int, args:tuple)->list** - Launches 'pool_size' functions at a time for all the 'args'. 'args' may be a tuple of tuples or tuple of values. If 'pool_size' not specified, then pool_size = number of CPU. Example:

		jobs_pool(
			msgbox
			, (
				'one'
				, 'two'
				, 'three'
				, 'four'
			)
			, 4
		)
	
	Difference between `jobs_batch` and `job_pool`:
	- `jobs_batch` - different functions with different arguments, waiting for the function is interrupted after the specified timeout and the results are returned as is, and where the function has not been executed yet, it returns *timeout*. All functions runs in parallel.
	- `jobs_pool` - same function for different arguments. Only the specified number of instances of the function is executed at the same time.
- **msgbox(msg:str, title:str=APP_NAME, ui:int=None, wait:bool=True, timeout:int=None)->int** - show messagebox and return user choice.
	Arguments:
	*msg* — text
	*title* — messagebox title
	*ui* — [interface flags](https://docs.microsoft.com/en-us/windows/desktop/api/winuser/nf-winuser-messagebox).
		Example: *ui = MB_ICONINFORMATION + MB_YESNO*
	*wait* — if set to False — continue task execution without waiting for user responce.
	*timeout* (in seconds) — automatically close messagebox. If messagebox is closed by timeout (no button is pressed by user) and *ui* contains more than one button (*MB_YESNO* for example) then it will return 32000.
	*dis_timeout* (in seconds) — hide the buttons for a specified number of seconds.
	Example:

		def test_msgbox():
			if msgbox('Can I have a cheeseburger?') == IDYES:
				print('Yes!')
			else:
				print('No :-(')

- **sound_play (fullpath:str, wait:bool)->str** - play .wav file. *wait* — do not pause task execution. If fullpath is a folder then pick random file.
- **time_now(template:str='%Y-%m-%d_%H-%M-%S')->str** - string with current time.
- **pause(sec:float)** - pause the execution of the task for the specified number of seconds. *interval* - time in seconds or a string specifying a unit like '5 ms' or '6 sec' or '7 min'.
- **var_set(var_name:str, value:str)** - save *value* of variable *var_name* to disk so it will persist between program starts.
- **var_get(var_name:str)->str** - retrieve variable value.
- **clip_set(txt:str)->** - copy text to clipboard.
- **clip_get()->str->** - get text from clipboard.
- **re_find(source:str, re_pattern:str, sort:bool=True)->list** - search in *source* with regular expression.
- **re_match(source:str, re_pattern:str, re_flags:int=re.IGNORECASE)->bool** - regexp match.
- **re_replace(source:str, re_pattern:str, repl:str='')** - replace in *source* all matches with *repl* string.
- **inputbox(message:str, title:str, is_pwd:bool=False)->str** - show a message with an input request. Returns the entered line or empty string if user pressed cancel.
	*is_pwd* — hide the typed text.
- **random_num(a, b)->int** - return a random integer in the range from a to b, including a and b.
- **random_str(string_len:int=10, string_source:str=None)->str** - generate a string of random characters with a given length.

### Keyboard

- **keys_pressed(hotkey:str)->bool** - is the key pressed?
- **keys_send(hotkey:str)** - press the key combination.
- **keys_write(text:str)** - write a text.

### Filesystem

**fullpath** means full name of file, for example 'c:\\\Windows\\\System32\\\calc.exe'

**IMPORTANT: always use double backslash "\\\" in paths!**

- **csv_read(fullpath:str, encoding:str='utf-8', fieldnames=None, delimiter:str=';', quotechar:str='"')->list** - read a CSV file and return the contents as a list of dictionaries.
- **csv_write(fullpath:str, content:list, fieldnames:tuple=None, encoding:str='utf-8', delimiter:str=';', quotechar:str='"', quoting:int=csv.QUOTE_MINIMAL)->str** - writes the list of dictionaries as a CSV file. If *fieldnames* is not specified - it takes the keys of the first dictionary as headers. Returns the full path to the file. *content* example:

		[
			{'name': 'some name',
			'number': 1}
			, {'name': 'another name',
			'number': 2}
			...	
		]
- **dir_delete(fullpath:str)** - delete directory.
- **dir_exists(fullpath:str)->bool** - directory exists?
- **dir_list(fullpath:str)->list:** - get list of files in directory.
	Examples:
	- Get a list of all log files in 'c:\\\Windows' **without** subfolders:

		dir_list('c:\\Windows\\*.log')

	- Get all log files in 'c:\\\Windows\\\' **with** subfolders:

		dir_list('c:\\Windows\\**\\*.log')

- **dir_size(fullpath:str, unit:str='b')->int** - folder size in specified units.
- **dir_zip(source:str, destination:str)->str** - zip the folder return the path to the archive.
- **drive_list()->list** - list of logical drives.
- **file_basename(fullpath:str)->str** - returns basename: file name without parent folder and extension.
- **file_backup(fullpath, folder:str=None)** - make copy of file with added timestamp.
	*folder* — place copy to this folder. If omitted — place in original folder.
- **file_copy(fullpath:str, destination:str)** - copy file to destination (fullpath or just folder).
- **file_delete(fullpath:str)** - delete file.
- **file_dialog(title:str=None, multiple:bool=False, default_dir:str='', default_file:str='', wildcard:str='', on_top:bool=True)** - Shows standard file dialog and returns fullpath or list of fullpaths if _multiple_ == True.
- **file_dir(fullpath:str)->str:** - get parent directory name of file.
- **file_exists(fullpath:str)->bool** - file exists?
- **file_ext(fullpath:str)->str** - file extension in lower case without dot.
- **file_hash(fullpath:str, algorithm:str='crc32')->str** - returns hash of file. *algorithm* - 'crc32' or 'md5'.
- **file_log(fullpath:str, message:str, encoding:str='utf-8', time_format:str='%Y.%m.%d %H:%M:%S')** - log *message* to *fullpath* file.
- **file_move(fullpath:str, destination:str)** - move file to destination folder or file.
- **file_name(fullpath:str)->str:** - get file name without directory.
- **file_name_fix(fullpath:str, repl_char:str='\_')->str** - replaces forbidden characters with _repl_char_. Removes leading and trailing spaces. Adds '\\\\?\\' for long paths.
- **file_read(fullpath:str)->str:** - get content of file.
- **file_rename(fullpath:str, dest:str)->str** - rename the file. *dest* is the full path or just a new file name without a folder.
- **file_size(fullpath:str, unit:str='b')->bool:** - get size of file in units (gb, mb, kb, b).
- **file_write(fullpath:str, content=str)** - write content to file.
- **file_zip(fullpath, destination:str)->str** - compress a file or files into an archive.
	*fullpath* — a string with a full file name or a list of files.
	*destiniation* — full path to the archive.
- **drive_free(letter:str, unit:str='GB')->int:** - get drive free space in units (gb, mb, kb, b).
- **is_directory(fullpath:str)->bool:** - fullpath is directory?
- **path_exists(fullpath:str)->bool:** - fullpath exists (no matter is it folder or file)?
- **dir_purge(fullpath:str, days:int=0, recursive=False, creation:bool=False, test:bool=False)** - delete files from folder *fullpath* older than n *days*.
	If *days* == 0 then delete all files.
	*creation* — use date of creation, otherwise use last modification date.
	*recursive* — delete from subfolders too.
	*test* — do not actually delete files, only print them.
- **temp_dir(new_dir:str=None)->str** - returns the path to the temporary folder. If *new_dir* is specified, it creates a subfolder in the temporary folder and returns its path.
- **temp_file(suffix:str='')->str** - returns the name for the temporary file.

### Network
- **domain_ip(domain:str)->list** - get a list of IP-addresses by domain name.
- **file_download(url:str, destination:str=None)->str:** - download file and return fullpath.
	*destination* — it may be None, fullpath or folder. If None then download to temporary folder with random name.
- **html_element(url:str, find_all_args)->str:** - download page and retrieve value of html element.
	*find_all_args* — dictionary that contain element information such as name or attributes.
	*number* - item number, if there are several of them found.
	Example:

		# Get the internal text of span element which has
		# the attribute itemprop="softwareVersion"
		find_all_args={
			'name': 'span'
			, 'attrs': {'itemprop':'softwareVersion'}
		}

	See *get_current_ip* in [task examples](#task-examples)
- **html_clean(html_str:str, separator=' ')->str** - removes HTML tags from string.
- **is_online(*sites, timeout:int=2)->int:** - checks if you have access to the Internet using HEAD queries to specified sites. If sites are not specified, then use google and yandex.
- **json_element(url:str, element:list)** - same as **html_element** but for json.
	*element* — a list with a map to desired item.
	Example: *element=['usd', 2, 'value']*
- **page_get(url:str, encoding:str='utf-8', post_file:str=None, post_hash:bool=False)->str:** - download page by url and return it's html as a string. *post_file* - send this file with POST request. *post_hash* - add the checksum of the file to request headers to check the integrity (see [Task Options](#task-options)).
- **pc_name()->str** - computer name.
- **url_hostname(url:str)->str** - extract the domain name from the URL.

### System
In the functions for working with windows, the *window* argument can be either a string with the window title or a number representing the window handle.

- **free_ram(unit:str='percent')** - amount of free memory. *unit* — 'kb', 'mb'... or 'percent'.
- **idle_duration(unit:str='msec')->int** - how much time has passed since user's last activity.
- **monitor_off()** - turn off the monitor.
- **registry_get(fullpath:str)** - get value from Windows Registry.
	*fullpath* — string like 'HKEY_CURRENT_USER\\Software\\Microsoft\\Calc\\layout'
- **window_activate(window=None)->int** - bring window to front. *window* may be a string with title or integer with window handle.
- **window_find(title:str)->list** - find window by title. Returns list of all found windows.
- **window_hide(window=None)->int** - hide window.
**- window_on_top(window=None, on_top:bool=True)->int** - makes the window to stay always on top.
- **window_show(window=None)->int** - show window.
- **window_title_set(window=None, new_title:str='')->int** - change window title from *cur_title* to *new_title*

### Mail
- **mail_check(server:str, login:str, password:str, folders:list=['inbox'], msg_status:str='UNSEEN')->tuple** - returns the number of new emails and a list of errors.
- **mail_download(server:str, login:str, password:str, output_dir:str, folders:list=['inbox'], trash_folder:str='Trash')->tuple** - downloads all messages to the specified folder. Successfully downloaded messages are moved to the IMAP *trash_folder* folder on the server. Returns the list with decoded message subjects and the list of errors.
- **mail_send(recipient:str, subject:str, message:str, smtp_server:str, smtp_port:int, smtp_user:str, smtp_password:str)** - send email.

### Process
- **app_start(app_path:str, app_args:str='', wait:bool=False)** - start application. If *wait=True* — returns process return code, if *False* — returns PID of created process.
	*app_path* — path to executable file.
	*app_args* — command-line arguments.
	*wait* — wait until application will be closed.
- **file_open(fullpath:str)** - open file or URL in default application.
- **process_close(process, timeout:int=10)** - soft completion of the process: first all windows belonging to the specified process are closed, and after the timeout (in seconds) the process itself is killed, if still exists.
- **process_exist(process, cmd:str=None)->bool** - checks whether the process exists and returns a PID or False. *cmd* is an optional command line search. This way you can distinguish between processes with the same executable but different command lines.
- **process_list(name:str='')->list** - get list of processes with that name. Item in list have this attributes:
	*pid* — PID of found process.
	*name* — short name of executable.
	*username* — username.
	*exe* — full path to executable.
	*cmdline* — command-line as list.
	Example — print PID of all Firefox processes:

		for proc in process_list('firefox.exe'):
			print(proc.pid)

- **process_cpu(pid:int, interval:int=1)->float** - CPU usage of process with specified PID. *interval* in seconds - how long to measure.
- **process_kill(process)** - kill process or processes. *process* may be an integer so only process with this PID will be terminated. If *process* is a string then kill every process with that name.
- **service_start(service:str, args:tuple=None)** - starts the service.
- **service_stop(service:str)->tuple** - stops the service.
- **service_running(service:str)->bool** - the service is up and running?
- **wts_message(sessionid:int, msg:str, title:str, style:int=0, timeout:int=0, wait:bool=False)** - sends message to WTS session. *style* - styles like in msgbox (0 - MB_OK). *timeout* - timeout in seconds (0 - no timeout). Returns same values as msgbox.
- **wts_cur_sessionid()->int** - returns SessionID of current process
- **wts_logoff(sessionid:int, wait:bool=False)->int** - logoffs session. *wait* - wait for completion.
- **wts_proc_list(process:str=None)->list** - returns list of DictToObj objects with properties: *.sessionid:int*, *.pid:int*, *.process:str* (name of exe file), *.pysid:obj*, *.username:str*, *.cmdline:list*. *process* - filter by process name.

### Cryptography
- **file_enc_write(fullpath:str, content:str, password:str, encoding:str='utf-8')->tuple**: — encrypts content with password and writes to a file. Adds salt as file extension. Returns status, fullpath/error.
- **file_enc_read(fullpath:str, password:str, encoding:str='utf-8')->tuple** - decrypts the contents of the file and returns status, content/error
- **file_encrypt(fullpath:str, password:str)->tuple** - encrypts file with password. Returns status, fullpath/error. Adds salt as file extension.
- **file_decrypt(fullpath:str, password:str)->tuple** - decrypts file with password. Returns status, fullpath/or error.

### Mikrotik RouterOS
- **routeros_query(query:list, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** - send query to router and get status and data. Please read wiki [wiki](https://wiki.mikrotik.com/wiki/Manual:API) about query syntax.
	Example — get information about interface 'bridge1':

		status, data = routeros_query(
			[
				'/interface/print'
				, '?name=bridge1'
			]
			, '192.168.0.1'
			, '8728'
			, 'admin'
			, 'pAsSworD'
		)

	Contents of *data*:

		[{'=.id': '*2',
		'=name': 'bridge1',
		'=type': 'bridge',
		'=mtu': 'auto',
		'=actual-mtu': '1500',
		'=l2mtu': '1596',
		'=mac-address': '6b:34:1B:2F:AA:21',
		'=last-link-up-time': 'jun/10/2019 10:33:35',
		'=link-downs': '0',
		'=rx-byte': '1325381950539',
		'=tx-byte': '2786508773388',
		'=rx-packet': '2216725736',
		'=tx-packet': '2703349720',
		'=rx-drop': '0',
		'=tx-drop': '0',
		'=tx-queue-drop': '0',
		'=rx-error': '0',
		'=tx-error': '0',
		'=fp-rx-byte': '1325315798948',
		'=fp-tx-byte': '0',
		'=fp-rx-packet': '2216034870',
		'=fp-tx-packet': '0',
		'=running': 'true',
		'=disabled': 'false',
		'=comment': 'lan'}]

- **routeros_send(cmd:str, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** - send command to router and get status and error.
	Example: get list of static items from specified address-list then delete them all:

		status, data = routeros_query(
			[
				'/ip/firewall/address-list/print'
				, '?list=my_list'
				, '?dynamic=false'
			]
			, device_ip='192.168.0.1'
			, device_user='admin'
			, device_pwd='PaSsWorD'
		)

		# check status and exit if there is error:
		if not status:
			print(f'Error: {data}')
			return

		# get list items from data:
		items = [i['=.id'] for i in data]

		# Now send commands for removing items from list.
		# Notice: cmd is list of lists
		routeros_send(
			[
				[
					'/ip/firewall/address-list/remove'
					, f'=.id={i}'
				] for i in items
			]
			, device_ip='192.168.0.1'
			, device_user='admin'
			, device_pwd='PaSsWorD'
		)	

- **routeros_find_send(cmd_find:list, cmd_send:list, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** - find all id's and perform some action on them.
	*cmd_find* — list with API *print* command to find what we need.
	*cmd_send* — list with action to perform.
	Example — remove all static entries from address-list *my_list*:

		routeros_find_send(
			cmd_find=[
				'/ip/firewall/address-list/print'
				, '?list=my_list'
				, '?dynamic=false'
			]
			, cmd_send=['/ip/firewall/address-list/remove']
			, device_ip='192.168.88.1'
			, device_user='admin'
			, device_pwd='PaSsW0rd'
		)

### Winamp
- **winamp_close** - close Winamp.
- **winamp_fast_forward** - fast forward 5 sec.
- **winamp_fast_rewind** - rewind 5 sec.
- **winamp_notification()** - show notification (for «Modern» skin only).
- **winamp_pause()** - pause.
- **winamp_play()** - play.
- **winamp_status()->str:** - playback status ('playing', 'paused' or 'stopped').
- **winamp_stop()** - stop.
- **winamp_toggle_always_on_top** - toggle always on top.
- **winamp_toggle_main_window** - show/hide Winamp window.
- **winamp_toggle_media_library** - show/hide media library.
- **winamp_track_info(sep:str='   ')->str:** - return string with samplerate, bitrate and channels. *sep* — separator.
- **winamp_track_length()->str:** - track length.
- **winamp_track_title(clean:bool=True)->str:** - current track title.

## Firefox extension
https://addons.mozilla.org/ru/firefox/addon/send-to-taskopy/

Extension adds item to context menu. With it you can run task in Taskopy. In object _data_ of this task will be passed this (if any):
	- data.page_url - URL of current page
	- data.link_url - URL of link that was clicked
	- data.editable - it is editable field?
	- data.selection - selectioin text
	- data.media_type - type of object (image, video etc)
	- data.src_url - link to object source.

_editable_ property is boolean, the rest are strings.

In the extension settings specify the URL of your task that will process data, for example:

	http://127.0.0.1:8275/task?get_data_from_browser

This task should have _data_ and _http=True_ properties.

Example - play Youtube video in PotPlayer:

	def get_data_from_browser(data, http=True, menu=False, log=False):
		if ('youtube.com' in data.link_url
		or 'youtu.be' in data.link_url):
			app_start(
				r'c:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe'
				, data.link_url
			)

## Context menu
You can add Taskopy to the *Send to* submenu of context menu.

There is a simple powershell script *Taskopy.ps1* in *resources* directory. You need to create a shortcut to this script in user directory:

	%APPDATA%\Microsoft\Windows\SendTo\

Task name is _send\_to_ by default. This task must have properties _data_ and _http_ so inside task you can access the full path of file via _data.fullpath_

Example - pass the file name to the task _virustotal\_demo_ from [Task examples](#task-examples):

	def send_to(data, http, menu=False, log=False):
		if file_ext(data.fullpath) in ['exe', 'msi']:
			virustotal_demo(data.fullpath)

Inside _virustotal\_demo_ you can see another way to pass a file name to a task - via **file_dialog**

## Help me
- [My StackOverflow question about menu by hotkey in wxPython](https://stackoverflow.com/questions/56079269/wxpython-popupmenu-by-global-hotkey) You can add a bounty if you have a lot of reputation.
- [Donate via PayPal](https://www.paypal.me/vikil)

## Task examples
- iPython + plugins
- Disk free space
- Current IP address
- Add IP-address to MikroTik router
- Virustotal check

Launch iPython (Jupyter) and copy all plugins to the clipboard to quickly paste and access all keywords:

	def iPython_demo(submenu='demo', task_name='iPython + plugins'):
		app_dir = r'd:\soft\taskopy'

		# Softly close existing process:
		process_close('ipython.exe', 3)
		# Run new process in new console:
		app_start('ipython', shell=True)
		plugs = dir_list('plugins\\*.py')
		plugs[:] = [
			'from ' + pl[:-3].replace('\\', '.')
			+ ' import *' for pl in plugs
		]
		for _ in range(100):
			if 'ipython' in window_title_get().lower():
				break
			pause('100 ms')
		pause(1)
		if not 'ipython'.lower() in window_title_get().lower():
			tprint('ipython not found')
			return
		keys_write(r'%cd {}'.format(app_dir))
		keys_send('enter')
		keys_write(
			r'%load_ext autoreload' + '\n'
			+ r'%autoreload 2' + '\n'
			+ '\n'.join(plugs)
		)
		pause('200 ms')
		keys_send('ctrl+enter')

 Check the free space on all local discs. Scheduled for a random interval between 30 and 45 minutes:
 
	def check_free_space_demo(submenu='demo'
	, schedule='every(30).to(45).minutes'):
		for d in drive_list():
			if drive_free(d) < 10:
				msgbox(f'low disk space: {d}')

Show message with current IP-address using dyndns.org:

	def get_current_ip():
		# Get the text of the HTML-tag 'body' from the checkip.dyndns.org page
		# html_element should return a string like 'Current IP Address: 11.22.33.44'
		ip = html_element(
			'http://checkip.dyndns.org/'
			, {'name':'body'}
		).split(': ')[1]
		tprint(f'Current IP: {ip}')
		msgbox(f'Current IP: {ip}', timeout=10)

Add the IP-address from the clipboard to the address-list of Mikrotik router:

	def add_ip_to_list():
		routeros_send(
			[
				'/ip/firewall/address-list/add'
				, '=list=my_list'
				, '=address=' + clip_get()
			]
			, device_ip='192.168.88.1'
			, device_user='admin'
			, device_pwd='PaSsWoRd'
		)
		msgbox('Done!', timeout=3)

Check MD5 hash of file in the Virustotal. You need to register to obtain free API key:

	def virustotal_demo(fullpath:str=None, submenu='demo'):
		APIKEY = 'your API key'
		if not fullpath:
			fullpath = file_dialog('Virustotal', wildcard='*.exe;*.msi')
			if not fullpath:
				return
		md5 = file_hash(fullpath, 'md5')
		scan_result = json_element(f'https://www.virustotal.com/vtapi/v2/file/report?apikey={APIKEY}&resource={md5}')
		if scan_result['response_code'] == 0:
			msgbox('Unknown file', timeout=3)
			return
		res = DictToObj(scan_result)
		for av in res.scans.keys():
			if res.scans[av]['detected']:
				print(f'{av}: ' + res.scans[av]['result'])
		msgbox(f'Result: {res.positives} of {res.total}', timeout=5)
