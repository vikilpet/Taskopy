

# Taskopy
### Python scheduler for Windows with hotkeys, tray menu, HTTP-server and many more.

<p align="center">
  <img src="https://i6.imageban.ru/out/2019/07/04/a6f6538a80bc7a62ab06ce5cea295a93.png">
</p>
<!---
![Tray icon menu](https://i6.imageban.ru/out/2019/07/04/a6f6538a80bc7a62ab06ce5cea295a93.png)
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
  msgbox('Take your pills', ui=MB_ICONEXCLAMATION)
```

## Contents
- [Installation](#installation)
- [Usage](#usage)
- [Task Options](#task-options)
- [Settings](#settings)
- [Keywords](#keywords)
  - [Miscelanneous](#miscelanneous)
  - [Filesystem](#filesystem)
  - [Network](#network)
  - [System](#system)
  - [Process](#process)
  - [Winamp](#winamp)
- [Help Me](#help-me)
- [Task Examples](#task-examples)


## Installation
### Option 1: binary
**Requirements:** Windows 7 and above.
You can download binary release but many of lousy antiviruses don't like python inside EXE so VirusTotal shows about 7 detects.

### Option 2: Python
**Requirements:** Python 3.7; Windows 7 and above.

Download project, install requirements:
```
pip install -r requirements.txt
```
[Download fresh sqlite-dll-win32-x86-...](https://www.sqlite.org/download.html) from *Precompiled Binaries for Windows* section and replace outdated sqlite3.dll (version < 3.24) in Python folder:
```
%userprofile%\AppData\Local\Programs\Python\Python37-32\DLLs\
```

Make shortcut to taskpy.py in Startup folder:
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
- **schedule** (None) — add to schedule. Functionality provided by [schedule project](https://github.com/dbader/schedule) so you better refer to their [documentation](https://schedule.readthedocs.io/en/stable/). Some examples:
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
    	# return this list as string divided by html <br> tag:
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


## Settings

Description of global application settings that you can change in
 *settiings.ini* file. Format: **setting** (default value) — description.

- **language** (en) — menu and msgbox language. Variants: en, ru.
- **editor** (notepad) — text editor for «Edit crontab» menu command.
- **server_ip** (127.0.0.1) — bind HTTP server to this local IP. For access from any address set to *0.0.0.0*.
**IT IS DANGEROUS TO ALLOW ACCESS FROM ANY IP!** Do not use *0.0.0.0* in public networks or limit access with firewall.
- **server_port** (80) — HTTP server port.


## Keywords
### Miscelanneous
- **msgbox(msg:str, title:str=APP_NAME, ui:int=None, wait:bool=True, timeout:int=None)->int** — show messagebox and return user choice. Arguments:
*msg* — text
*title* — messagebox title
*ui* — [interface flags](https://docs.microsoft.com/en-us/windows/desktop/api/winuser/nf-winuser-messagebox). Example: *ui = MB_ICONINFORMATION + MB_YESNO*
*wait* — if set to True — continue task execution without waiting for user responce.
*timeout* (in seconds) — automatically close messagebox. If messagebox is closed by timeout (no button is pressed by user) and *ui* contains more than one button (*MB_YESNO* for example) then it will return 32000.
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
- **time_sleep(sec:float)** — pause in seconds.
- **var_set(var_name:str, value:str)** — save *value* of variable *var_name* to disk so it will persist between program starts.
- **var_get(var_name:str)->str** — retrieve variable value.
- **clip_set(txt:str)->** — copy text to clipboard.
- **clip_get()->str->** — get text from clipboard.
- **re_find(source:str, re_pattern:str, sort:bool=True)->list** — 
search in *source* with regular expression.
- **re_replace(source:str, re_pattern:str, repl:str='')** — replace in *source* all matches with *repl* string.
- **email_send(recipient:str, subject:str, message:str, smtp_server:str, smtp_port:int, smtp_user:str, smtp_password:str)** — send email.

### Filesystem

**fullpath** means full name of file, for example 'c:\\\Windows\\\System32\\\calc.exe'

**IMPORTANT: always use double backslash in paths!**

- **dir_delete(fullpath:str):** — delete directory.
- **dir_list(fullpath:str)->list:** — get list of files in directory.
 Examples:
    - Get list of all log files in 'c:\\\Windows' **without** subfolders:
    ```python
    dir_list('c:\\Windows\\*.log')
    ```
    - Get all log files in 'c:\\\Windows\\\' **with** subfolders:
    ```python
    dir_list('c:\\Windows\\**\\*.log')
    ```
- **file_backup(fullpath, folder:str=None):** — make copy of file with added timestamp.
*folder* — place copy to this folder. If omitted — place in original folder.
- **file_copy(fullpath:str, destination:str):** — copy file to destination (fullpath or just folder)/
- **file_delete(fullpath:str):** — delete file.
- **file_dir(fullpath:str)->str:** — get parent directory name of file.
- **file_move(fullpath:str, destination:str):** — move file to destination folder or file.
- **file_name(fullpath:str)->str:** — get file name without directory.
- **file_read(fullpath:str)->str:** — get content of file.
- **file_size(fullpath:str, unit:str='b')->bool:** — get size of file in units (gb, mb, kb, b).
- **file_write(fullpath:str, content=str):** — write content to file.
- **free_space(letter:str, unit:str='GB')->int:** — get disk free space in units (gb, mb, kb, b).
- **is_directory(fullpath:str)->bool:** — fullpath is directory?
- **path_exists(fullpath:str)->bool:** — fullpath exists (no matter is it folder or file)?
- **purge_old(fullpath:str, days:int=0, recursive=False, creation:bool=False, test:bool=False):** — delete files from folder *fullpath* older than n *days*.
If *days* == 0 then delete all files.
*creation* — use date of creation, otherwise use last modification date.
*recursive* — delete from subfolders too.
*test* — do not actually delete files, only print them.

### Network
- **file_download(url:str, destination:str=None)->str:** — download file and return fullpath.
*destination* — it may be None, fullpath or folder. If None then download to temporary folder with random name.
- **html_element_get(url:str, find_all_args)->str:** — download page and retrieve value of html element.
*find_all_args* — dictionary that contain element information such as name or attributes. Example:
```pyhon
# Get "123" from html tag <span itemprop="softwareVersion">123</span>
find_all_args={
	'name': 'span'
	, 'attrs': {'itemprop':'softwareVersion'}
}
```
See *get_current_ip* in [task examples](#task-examples)
- **json_element_get(url:str, element:list):** — same as **html_element_get** but for json.
*element* — list with map to needed element. Example: element=['usd', 2, 'value']
- **page_get(url:str, encoding:str='utf-8')->str:** — download page by url and return it's html as a string.

### System
- **registry_get(fullpath:str)** — get value from Windows Registry. fullpath is string like 'HKEY_CURRENT_USER\\Software\\Microsoft\\Calc\\layout'
- **window_title_set(cur_title:str, new_title:str):** — change window title from *cur_title* to *new_title*

### Process
- **app_start(app_path:str, wait=False):** — start application.
*app_path* — fullpath to executable file.
*wait* — wait until application will be closed.
- **file_open(fullpath:str):** — open file or URL in default application.

### Winamp
- **winamp_notification():** — show notification (modern skin).
- **winamp_pause():** — pause.
- **winamp_play():** — play.
- **winamp_status()->str:** — playback status ('playing', 'paused' or 'stopped').
- **winamp_stop():** — stop.
- **winamp_track_info(sep:str='   ')->str:** — return string with samplerate, bitrate and channels.
- **winamp_track_length()->str:** — track length.
- **winamp_track_title(clean:bool=True)->str:** — current track title.
 
## Help me
- Please correct my spelling mistakes because I am not a native English speaker.
- [My StackOverflow question about menu by hotkey in wxPython](https://stackoverflow.com/questions/56079269/wxpython-popupmenu-by-global-hotkey) You can add a bounty if you have a lot of reputation.
- [Donate via PayPal](https://www.paypal.me/vikil)

## Task examples
```python
# Start iPython and copy all Taskopy plugins imports to clipboard so
# it is easy to paste in iPython and get access to all
# functions from all plugins:
def iPython():
	app_start('ipython')
	plugs = dir_list('plugins\\*.py')
	plugs[:] = [
		'from ' + pl[:-3].replace('\\', '.')
		+ ' import *' for pl in plugs
	]
	# also enable autoreload:
	clip_set(
		'%load_ext autoreload' + '\n'
		+ '%autoreload 2' + '\n'
		+ '\n'.join(plugs) + '\n'
	)


# Check free space on all disks.
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
			+ f'e: {free_space("g")}\n'
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
	# html_element_get should return string 'Current IP Address: 11.22.33.44'
	ip = html_element_get(
		'http://checkip.dyndns.org/'
		, {'name':'body'}
	).split(': ')[1]
	print(f'Current IP: {ip}')
	msgbox(f'Current IP: {ip}', timeout=10)

# Запускаем калькулятор и меняем его заголовок на курс продажи
# доллара в Сбербанке. Назначаем выполнение задачи на клик
# левой клавишей мыши по иконке:
def demo_task_4(left_click=True):
	# Запускаем калькулятор:
	app_start(r'calc.exe')
	# Скачиваем json по которому грузится список валют
	# и получаем из него курс продажи доллара:
	usd = json_element_get(
		'https://www.sberbank.ru/portalserver/proxy/?pipe=shortCachePipe&url=http://localhost/rates-web/rateService/rate/current%3FregionId%3D77%26currencyCode%3D840%26currencyCode%3D978%26rateCategory%3Dbeznal'
		, ['beznal', '840', '0', 'sellValue']
	)
	# Теперь меняем заголовок калькулятора на USD={найденное значение}
	window_title_set('Калькулятор', f'USD={usd}')

```

<!---
2019-07-05_03-15-57
 -->