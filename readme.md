# Taskopy
### Python scheduler for Windows with hotkeys, tray menu, HTTP-server and many more.

<p align="center">
	<img src="https://i6.imageban.ru/out/2019/07/04/a6f6538a80bc7a62ab06ce5cea295a93.png">
</p>
<!---
2019-08-19_22-22-53
-->
Run your python code with hotkey or by HTTP-request just like that:

```python
def my_task(hotkey='ctrl+shift+t', http=True):
	print('This is my code!')
```
Then press Ctrl+Shift+T or open in browser URL http://127.0.0.1/task?my_task and your task will be executed.

Another example: show message box every day at 10:30 and hide this task from menu:
```python
def my_another_task(schedule='every().day.at("10:30")', menu=False):
	msgbox('Take the pills', ui=MB_ICONEXCLAMATION)
```

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
	- [Process](#process)
	- [Winamp](#winamp)
	- [Mikrotik RouterOS](#mikrotik-routeros)
- [Help Me](#help-me)
- [Task Examples](#task-examples)

## Installation
### Option 1: binary file

**Requirements:** Windows 7 and above.
You can [download](https://github.com/vikilpet/Taskopy/releases) archive with binary release but many of lousy antiviruses don't like python inside EXE so VirusTotal shows about 7 detects.

### Option 2: Python
**Requirements:** Python 3.7.4; Windows 7 and above.

Download project, install requirements:
```
pip install -r requirements.txt
```
Make shortcut to taskopy.py in Startup folder:
```
%userprofile%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\
```
In shortcut options choose *Run: minimized* option and change shortcut icon to resources\logo.ico

## Usage
Open crontab.py in your favorite text editor and create your task as function with arguments:
```python
def demo_task_3('left_click'=True, log=False):
	app_start('calc.exe')
```
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
	```python
	schedule='every().hour'
	```
	Run task every wednesday at 13:15:
	```python
	schedule='every().wednesday.at("13:15")'
	```
	You can set multiple schedule at once with list:
	```python
	schedule=['every().wednesday.at("18:00")', 'every().friday.at("17:00")']
	```
- **active** (True) — to enable-disable task.
- **startup** (False) — run at taskopy startup.
- **sys_startup** (False) — run at Windows startup (uptime is less than 3 min).
- **left_click** (False) — assign to mouse left button click on tray icon.
- **log** (True) — log to console and file.
- **single** (True) — allow only one instance of running task.
- **submenu** (None) — place task in this sub menu.
- **result** (False) — task should return some value. Use together with http option to get page with task results.
- **http** (False) — run task by HTTP request. HTTP request syntax: http://127.0.0.1/task?your_task_name where «your_task_name» is the name of function from crontab.
	If option **result** also enabled then HTTP request will show what task will return or 'OK' if there is no value returned.
	Example:
	```python
	def demo_task_4(http=True, result=True):
		# Get list of files and folders in Taskopy folder:
		listing = dir_list('*')
		# return this list as string divided by html br tag:
		return '<br>'.join(listing)
	```
	Result in browser:
	```
	backup
	crontab.py
	log
	resources
	settings.ini
	taskopy.exe
	```
	Also see [settings](#settings) section for IP and port bindings.
- **caller** — place this option before other options and in task body you will know who actually launched task this time. Possible values: http, menu, scheduler, hotkey. See *def check_free_space* in [Task Examples](#task-examples).
- **data** — use together with **http** and place this option before other options and it will filled with HTTP request data and you will able to work with them in task body.
	*data.client_ip* — IP-address of request.
	*data.path* — full relative path of request including */task?*
	*data* will contain all HTTP-request headers such as *User-Agent*, 	*Accept-Language* etc.
	If you will construst request URL with common scheme *&param1=value1&param2=value2* they will be processed and added to data and you can access them in task body as data.param1, data.param2.
	Example:
	```Python
	def alert(data, http=True, single=False, menu=False):
		msgbox(
			data.text
			# Use data.title if possible otherwise just use 'Alert' as message title.
			, title=data.title if data.title else 'Alert'
			, dis_timeout=1
		)
	```
	Type in address bar of browser something like this:
	http://127.0.0.1/task?alert&text=MyMsg&title=MyTitle
	and you will see messagebox with title and text from URL.
- **idle** — Perform the task when the user is idle for the specified time. For example, *idle='5 min'* - run when the user is idle for 5 minutes. The task is executed only once during the inactivity.
- **err_threshold** — do not report any errors in the task until this threshold is exceeded.

## Settings
Global settings are stored in *settiings.ini* file.

Format: **setting** (default value) — description.

- **language** (en) — menu and msgbox language. Variants: en, ru.
- **editor** (notepad) — text editor for «Edit crontab» menu command.
- **hide_console** — hide the console window.
- **server_ip** (127.0.0.1) — bind HTTP server to this local IP. For access from any address set to *0.0.0.0*.
	**IT IS DANGEROUS TO ALLOW ACCESS FROM ANY IP!** Do not use *0.0.0.0* in public networks or limit access with firewall.
- **white_list** (127.0.0.1) — a list of IP addresses separated by commas from which requests are received.
- **server_port** (80) — HTTP server port.

## Keywords
### Miscelanneous
- **msgbox(msg:str, title:str=APP_NAME, ui:int=None, wait:bool=True, timeout:int=None)->int** — show messagebox and return user choice.
	Arguments:
	*msg* — text
	*title* — messagebox title
	*ui* — [interface flags](https://docs.microsoft.com/en-us/windows/desktop/api/winuser/nf-winuser-messagebox).
		Example: *ui = MB_ICONINFORMATION + MB_YESNO*
	*wait* — if set to False — continue task execution without waiting for user responce.
	*timeout* (in seconds) — automatically close messagebox. If messagebox is closed by timeout (no button is pressed by user) and *ui* contains more than one button (*MB_YESNO* for example) then it will return 32000.
	*dis_timeout* (in seconds) — hide the buttons for a specified number of seconds.
	Example:
	```python
	def test_msgbox():
		if msgbox('I can have cheeseburger?') == IDYES:
			print('Yes!')
		else:
			print('No :-(')
	```
- **sound_play (fullpath:str, wait:bool)->str** — play .wav file. *wait* — do not pause task execution.
- **time_now(template:str='%Y-%m-%d_%H-%M-%S')->str** — string with current time.
- **pause(sec:float)** — pause the execution of the task for the specified number of seconds. *interval* - time in seconds or a string specifying a unit like '5 ms' or '6 sec' or '7 min'.
- **var_set(var_name:str, value:str)** — save *value* of variable *var_name* to disk so it will persist between program starts.
- **var_get(var_name:str)->str** — retrieve variable value.
- **clip_set(txt:str)->** — copy text to clipboard.
- **clip_get()->str->** — get text from clipboard.
- **re_find(source:str, re_pattern:str, sort:bool=True)->list** — search in *source* with regular expression.
- **re_replace(source:str, re_pattern:str, repl:str='')** — replace in *source* all matches with *repl* string.
- **email_send(recipient:str, subject:str, message:str, smtp_server:str, smtp_port:int, smtp_user:str, smtp_password:str)** — send email.
- **inputbox(message:str, title:str, is_pwd:bool=False)->str** — show a message with an input request. Returns the entered line or empty string if user pressed cancel.
	*is_pwd* — hide the typed text.
- **random_num(a, b)->int** — return a random integer in the range from a to b, including a and b.
- **random_str(string_len:int=10, string_source:str=None)->str** — generate a string of random characters with a given length.

### Keyboard

- **keys_pressed(hotkey:str)->bool** — is the key pressed?
- **keys_send(hotkey:str)** — press the key combination.
- **keys_write(text:str)** — write a text.

### Filesystem

**fullpath** means full name of file, for example 'c:\\\Windows\\\System32\\\calc.exe'

**IMPORTANT: always use double backslash "\\\" in paths!**

- **csv_read(fullpath:str, encoding:str='utf-8', fieldnames=None, delimiter:str=';', quotechar:str='"')->list** — read a CSV file and return the contents as a list of dictionaries.
- **dir_delete(fullpath:str)** — delete directory.
- **dir_list(fullpath:str)->list:** — get list of files in directory.
	Examples:
	- Get a list of all log files in 'c:\\\Windows' **without** subfolders:
	```python
	dir_list('c:\\Windows\\*.log')
	```
	- Get all log files in 'c:\\\Windows\\\' **with** subfolders:
	```python
	dir_list('c:\\Windows\\**\\*.log')
	```
- **dir_zip(source:str, destination:str)->str** — zip the folder return the path to the archive.
- **file_backup(fullpath, folder:str=None)** — make copy of file with added timestamp.
	*folder* — place copy to this folder. If omitted — place in original folder.
- **file_copy(fullpath:str, destination:str)** — copy file to destination (fullpath or just folder).
- **file_delete(fullpath:str)** — delete file.
- **file_dir(fullpath:str)->str:** — get parent directory name of file.
- **file_log(fullpath:str, message:str, encoding:str='utf-8', time_format:str='%Y.%m.%d %H:%M:%S')** — log *message* to *fullpath* file.
- **file_move(fullpath:str, destination:str)** — move file to destination folder or file.
- **file_name(fullpath:str)->str:** — get file name without directory.
- **file_read(fullpath:str)->str:** — get content of file.
- **file_rename(fullpath:str, dest:str)->str** — rename the file. *dest* is the full path or just a new file name without a folder.
- **file_size(fullpath:str, unit:str='b')->bool:** — get size of file in units (gb, mb, kb, b).
- **file_write(fullpath:str, content=str)** — write content to file.
- **file_zip(fullpath, destination:str)->str** — compress a file or files into an archive.
	*fullpath* — a string with a full file name or a list of files.
	*destiniation* — full path to the archive.
- **free_space(letter:str, unit:str='GB')->int:** — get disk free space in units (gb, mb, kb, b).
- **is_directory(fullpath:str)->bool:** — fullpath is directory?
- **path_exists(fullpath:str)->bool:** — fullpath exists (no matter is it folder or file)?
- **purge_old(fullpath:str, days:int=0, recursive=False, creation:bool=False, test:bool=False)** — delete files from folder *fullpath* older than n *days*.
	If *days* == 0 then delete all files.
	*creation* — use date of creation, otherwise use last modification date.
	*recursive* — delete from subfolders too.
	*test* — do not actually delete files, only print them.

### Network
- **domain_ip(domain:str)->list** — get a list of IP-addresses by domain name.
- **file_download(url:str, destination:str=None)->str:** — download file and return fullpath.
	*destination* — it may be None, fullpath or folder. If None then download to temporary folder with random name.
- **html_element(url:str, find_all_args)->str:** — download page and retrieve value of html element.
	*find_all_args* — dictionary that contain element information such as name or attributes. Example:
	```python
	# Get the internal text of span element which has
	# the attribute itemprop="softwareVersion"
	find_all_args={
		'name': 'span'
		, 'attrs': {'itemprop':'softwareVersion'}
	}
	```
	See *get_current_ip* in [task examples](#task-examples)
- **is_online(*sites, timeout:int=2)->int:** — checks if you have access to the Internet using HEAD queries to specified sites. If sites are not specified, then use google and yandex.
- **json_element(url:str, element:list)** — same as **html_element** but for json.
	*element* — a list with a map to desired item.
	Example: *element=['usd', 2, 'value']*
- **page_get(url:str, encoding:str='utf-8')->str:** — download page by url and return it's html as a string.
- **url_hostname(url:str)->str** — extract the domain name from the URL.

### System
In the functions for working with windows, the *window* argument can be either a string with the window title or a number representing the window handle.

- **free_ram(unit:str='percent')** — amount of free memory. *unit* — 'kb', 'mb'... or 'percent'.
- **idle_duration(unit:str='msec')->int** — how much time has passed since user's last activity.
- **monitor_off()** — turn off the monitor.
- **registry_get(fullpath:str)** — get value from Windows Registry.
	*fullpath* — string like 'HKEY_CURRENT_USER\\Software\\Microsoft\\Calc\\layout'
- **window_activate(window=None)->int** — bring window to front. *window* may be a string with title or integer with window handle.
- **window_find(title:str)->list** — find window by title. Returns list of all found windows.
- **window_hide(window=None)->int** — hide window.
**- window_on_top(window=None, on_top:bool=True)->int** — makes the window to stay always on top.
- **window_show(window=None)->int** — show window.
- **window_title_set(window=None, new_title:str='')->int** — change window title from *cur_title* to *new_title*

### Process
- **app_start(app_path:str, app_args:str='', wait:bool=False)** — start application. If *wait=True* — returns process return code, if *False* — returns PID of created process.
	*app_path* — path to executable file.
	*app_args* — command-line arguments.
	*wait* — wait until application will be closed.
- **file_open(fullpath:str)** — open file or URL in default application.
- **process_close(process, timeout:int=10)** — soft completion of the process: first all windows belonging to the specified process are closed, and after the timeout (in seconds) the process itself is killed, if still exists.
- **process_exist(process, cmd:str=None)->bool** — checks whether the process exists and returns a PID or False. *cmd* is an optional command line search. This way you can distinguish between processes with the same executable but different command lines.
- **process_list(name:str='')->list** — get list of processes with that name. Item in list have this attributes:
	*pid* — PID of found process.
	*name* — short name of executable.
	*username* — username.
	*exe* — full path to executable.
	*cmdline* — command-line as list.
	Example — print PID of all Firefox processes:
	```python
	for proc in process_list('firefox.exe'):
		print(proc.pid)
	```
- **process_cpu(pid:int, interval:int=1)->float** — CPU usage of process with specified PID. *interval* in seconds - how long to measure.
- **process_kill(process)** — kill process or processes. *process* may be an integer so only process with this PID will be terminated. If *process* is a string then kill every process with that name.

### Winamp
- **winamp_close** — close Winamp.
- **winamp_fast_forward** — fast forward 5 sec.
- **winamp_fast_rewind** — rewind 5 sec.
- **winamp_notification()** — show notification (for «Modern» skin only).
- **winamp_pause()** — pause.
- **winamp_play()** — play.
- **winamp_status()->str:** — playback status ('playing', 'paused' or 'stopped').
- **winamp_stop()** — stop.
- **winamp_toggle_always_on_top** — toggle always on top.
- **winamp_toggle_main_window** — show/hide Winamp window.
- **winamp_toggle_media_library** — show/hide media library.
- **winamp_track_info(sep:str='   ')->str:** — return string with samplerate, bitrate and channels. *sep* — separator.
- **winamp_track_length()->str:** — track length.
- **winamp_track_title(clean:bool=True)->str:** — current track title.

### Mikrotik RouterOS
- **routeros_query(query:list, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** — send query to router and get status and data. Please read wiki [wiki](https://wiki.mikrotik.com/wiki/Manual:API) about query syntax.
	Example — get information about interface 'bridge1':
	```python
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
	```
	Contents of *data*:
	```
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
	```
- **routeros_send(cmd:str, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** — send command to router and get status and error.
	Example: get list of static items from specified address-list then delete them all:
	```python
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
	```
- **routeros_find_send(cmd_find:list, cmd_send:list, device_ip:str=None, device_port:str='8728', device_user:str='admin', device_pwd:str='')** — find all id's and perform some action on them.
	*cmd_find* — list with API *print* command to find what we need.
	*cmd_send* — list with action to perform.
	Example — remove all static entries from address-list *my_list*:
	```python
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
	```

## Help me
- [My StackOverflow question about menu by hotkey in wxPython](https://stackoverflow.com/questions/56079269/wxpython-popupmenu-by-global-hotkey) You can add a bounty if you have a lot of reputation.
- [Donate via PayPal](https://www.paypal.me/vikil)

## Task examples
```python
# Launch iPython and copy all plugins to the clipboard
# to quickly paste and access all keywords:
def iPython(submenu='WIP'):
	# kill existing process:
	process_kill('ipython.exe')
	# start new process:
	app_start('ipython')
	# get all plugins from 'plugins' folder:
	plugs = dir_list('plugins\\*.py')
	plugs[:] = [
		'from ' + pl[:-3].replace('\\', '.')
		+ ' import *' for pl in plugs
	]
	# give the process time to boot up:
	time_sleep(1.5)
	# import from plug-ins:
	keys_write(
		r'%load_ext autoreload' + '\n'
		+ r'%autoreload 2' + '\n'
		+ '\n'.join(plugs)
	)
	time_sleep(0.2)
	# send control + enter to complete the command:
	keys_send('ctrl+enter')


# Check the free space on all discs.
# Add 'caller' to task arguments so inside task you can check
# how task was called.
# Scheduled to random interval between 30 and 45 minutes
def check_free_space(caller, schedule='every(30).to(45).minutes'):
	# If task was runned from menu then show messagebox
	if caller == 'menu':
		msg = (
			'Free space in GB:\n'
			+ f'c: {free_space("c")}\n'
			+ f'd: {free_space("d")}\n'
			+ f'e: {free_space("e")}\n'
		)
		# messagebox will auto-closed after 3 seconds:
		msgbox(msg, timeout=3)
	else:
		# Task is launched by scheduler
		# check free space in C, D, E and show alert only if
		# there is less than 3 GB left:
		for l in 'cde':
			if free_space(l) < 3:
				msgbox(f'Low disk space: {l.upper()}')

def get_current_ip():
	# Get the text of the HTML-tag 'body' from the checkip.dyndns.org page
	# html_element should return a string like 'Current IP Address: 11.22.33.44'
	ip = html_element(
		'http://checkip.dyndns.org/'
		, {'name':'body'}
	).split(': ')[1]
	print(f'Current IP: {ip}')
	msgbox(f'Current IP: {ip}', timeout=10)

# Add the IP-address from the clipboard to the address-list
# of Mikrotik router
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
    msgbox('Done!', timeout=5)
```