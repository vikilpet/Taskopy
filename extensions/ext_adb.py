r'''
Just binding to ADB commands, nothing special.

## How to install ADB

Download and unzip SDK command line tools:

	https://developer.android.com/tools/releases/platform-tools

Activate developer mode on phone (7 taps on serial number).
In *Developer options* enable *USB debugging*.  
Run this in CMD to find out the ID of your phone:

	%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe devices

To stop server (in cmd):

	%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe kill-server

Add the server to startup:

	%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe start-server

Examples:

	asrt(adb_run(r'adb shell getprop ro.build.ab_update'), (True, 'true\n'))

## Connect over Wi-Fi

Connect via USB and run `adb tcpip 5555` then run `adb connect 192.168.x.x:5555`
(phone IP address). In this case *dev_id* is *192.168.x.x:5555*.  

## Naming convention:

*apath* - a full path on an android device.  
*pcpath* - a PC full path.  

## List of devices

	print(adb_run('devices -l')[1])

## List of settings

*namespace* is one of *system, secure, global*:

	print(adb_run('shell settings list namespace')[1])


## Problems:

0 byte previews on some Android versions. What doesn't work:

- Reboot
- Clear cache in *Files*
- Clear *OpenCamera* & *Files* cache and storage in app settings

## Some ADB commands

Swipe up: `shell input touchscreen swipe 530 1920 530 1120`  
Press keys: `shell input text abc`  
Call the PIN keypad when the screen is locked: `shell input keyevent 82`  
Lock phone: `shell input keyevent KEYCODE_POWER`  

## Links:

- broadcasts: https://developer.android.com/about/versions/11/reference/broadcast-intents-30
- key codes: https://developer.android.com/reference/android/view/KeyEvent#KEYCODE_BUTTON_START
- key codes web: https://developer.mozilla.org/en-US/docs/Web/API/UI_Events/Keyboard_event_key_values
- Google OEM USB drivers: https://developer.android.com/studio/run/oem-usb

'''
from plugins.tools import *
from plugins.plugin_network import *
from plugins.plugin_filesystem import *
from plugins.plugin_process import *
from plugins.plugin_system import *

_ADB = path_get(r'%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe')

def adb_run(cmd:list|tuple|str, **kwargs)->tuple[bool, str]:
	r'''
	Returns (True, 'output')
	'''
	if isinstance(cmd, str): cmd = cmd.split()
	if cmd[0].lower() in ('adb', 'adb.exe'): cmd.pop(0)
	if file_ext(cmd[0]) == 'exe' or cmd[0] in ('fastboot', 'mke2fs'):
		cmd = [
			os.path.join(file_dir(_ADB), cmd[0])
			, *[str(c) for c in cmd[1:]]
		]
	else:
		cmd = [_ADB, *[str(c) for c in cmd] ]
	if kwargs.get('dev_id'):
		cmd.insert(1, kwargs['dev_id'])
		cmd.insert(1, '-s')
	if is_con(): qprint('adb ' + ' '.join(cmd[1:]))
	ret, out, err = proc_wait(' '.join(cmd), encoding='utf-8')
	out = err if err else out
	if err and is_con(): tprint(f'error: {err}')
	return ret == 0, out.strip()

def adb_dir_files(adir:str='/sdcard/', ext:str|None=None
, afilter=None, **kwargs)->tuple:
	r'''
	Returns (True, [list of files]) or (False, 'error text')  
	*ext*:str or list or tuple - only files with this extension(s).  
	*adir* - directory on Android, for example:
		
		adir='/sdcard/DCIM/Camera'

	*afilter* - function to check file against, for example
	files that starts with *IMG*:

		afilter=lambda f: file_name(f).startswith('IMG')

	'''
	if isinstance(ext, str): ext = (ext, )
	cmd = ('shell', 'ls', '-Rl', adir)
	status, data = adb_run(cmd, **kwargs)
	if not status: return False, data
	afiles = []
	for apath in data.splitlines():
		if apath.startswith('/') and apath.endswith(':'):
			cur_dir = apath[:-1] + '/'
			continue
		if not apath.startswith('-'): continue
		afile = cur_dir + apath.split(':')[1][3:]
		if ext and (not file_ext(afile) in ext): continue
		if afilter and (not afilter(afile)): continue
		afiles.append(afile)
	return True, afiles

def adb_del(apath:str, **kwargs)->tuple:
	r'''
	Deletes file on Android and returns (True, '') on success.
	'''
	cmd = ('shell', 'rm', '-f', "'" + apath + "'")
	status, data = adb_run(cmd, **kwargs)
	if not status: return False, data
	return adb_rescan(file_dir(apath), **kwargs)

def adb_pull(apath:str, pcpath:str, **kwargs)->tuple:
	r'''
	Copy file from Android to PC. Returns full path on PC.  
	*apath* - full path from Android.  
	*pcpath* - PC directory or the full name of the file.  
	'''
	dst_file = pcpath
	if dir_exists(pcpath):
		dst_file = os.path.join(pcpath, file_name(apath))
	cmd = ('pull', apath, dst_file)
	status, data = adb_run(cmd, **kwargs)
	if not status: return False, data
	return True, dst_file

def adb_pull_del(apath:str, pcpath:str, **kwargs)->tuple:
	r'''
	Moves file from Android to PC (deletes on Android).  
	Returns (True, 'pc full path') or (False, 'error text').  
	'''
	status, dst_file = adb_pull(apath=apath, pcpath=pcpath, **kwargs)
	if not status: return False, dst_file
	if not( file_exists(dst_file) and file_size(dst_file) > 1):
		return False, 'bad dst file'
	status, data = adb_del(apath, **kwargs)
	if not status: return False, data
	return True, dst_file

def adb_dir_create(apath:str, **kwargs)->tuple:
	return adb_run(('shell', 'mkdir', f'"{apath}"'), **kwargs)

def adb_dir_delete(apath:str, **kwargs)->tuple:
	return adb_run(f'shell rm -r {apath}', **kwargs)

def adb_push(pcpath:str, apath:str, **kwargs)->tuple[bool, str]:
	r'''
	Copies file from PC to Android. Returns full path on Android.  
	Returns (True, 'normalized/apath')  
	*apath* - directory on Android.  
	*pcpath* - PC directory or the full name of the file.  
	'''
	apath = apath.replace('\\', '/').rstrip('/')
	if is_dir := dir_exists(pcpath):
		apath = apath + '/' + file_name(pcpath.rstrip('\\'))
		status, data = adb_dir_create(apath, **kwargs)
	for fpath in (dir_files(pcpath) if is_dir else (pcpath,)):
		fname = file_name(fpath)
		status, data = adb_run(
			('push', '"' + fpath + '"', ''.join(('"', apath, '/', fname, '"')))
			, **kwargs
		)
		if not status: return False, f'push error: {data}'
		time_sleep('300 ms')
	status, data = adb_rescan(apath, **kwargs)
	if not status: return False, data
	return True, apath

def adb_rescan(apath:str, **kwargs)->tuple:
	r'''
	Rescans files in given Android directory.
	'''
	return adb_run(
		'adb shell am broadcast'
		+ ' -a android.intent.action.MEDIA_SCANNER_SCAN_FILE'
		+ f' -d "file:///{apath}"'
		, **kwargs
	)

def adb_acc_rot(enable:bool, **kwargs)->bool:
	r'''
	Toggles the automatic screen rotation
	'''
	return adb_run(
		'shell settings put system accelerometer_rotation '
		+ ('1' if enable else '0')
		, **kwargs
	)[0]

def adb_screen_rotate(value:int=2, dis_auto:bool=True, **kwargs)->bool:
	r'''
	Rotates the screen. Returns `True` on success
	Value variants:

	- 0 - normal
	- 1 - 90 CW
	- 2 - 180
	- 3 - 90 CCW

	*dis_auto* - disable auto-rotation.  

	'''
	if not adb_acc_rot(False, **kwargs): return False
	return adb_run(f'shell settings put system user_rotation {value}', **kwargs)[0]

def adb_dev_list()->list:
	r'''
	Returns list of connected Android devices.
	'''
	status, data = adb_run('devices')
	if not status: return []
	devices = []
	for line in data.rstrip().splitlines()[1:]:
		dev_id, mode = line.split()
		tdebug('listing:', dev_id, mode)
		if mode == 'device': devices.append(dev_id)
	return devices

def adb_screenshot(dst_dir:str='tmp', **kwargs)->str:
	r'''
	Make a screenshot. Returns the path to the screenshot on the PC.
	'''
	apath = f'/sdcard/Pictures/Screenshots/{time_str()}.png'
	status, data = adb_run(f'shell screencap {apath}', **kwargs)
	tdebug(data)
	if not status: return ''
	if dst_dir == 'tmp': dst_dir = temp_dir()
	pcpath = file_dir_repl(apath, dst_dir)
	adb_pull(apath, pcpath, **kwargs)
	return pcpath

def adb_screen_bright(level:int, **kwargs)->bool:
	r'''
	Sets the screen brightness level (0-255).  
	Note: the lowest value can be 1 instead of 0.  
	'''
	status, _ = adb_run(f'shell settings put system screen_brightness {level}'
	, **kwargs)
	return status

def adb_server_restart(**kwargs)->tuple[bool, str]:
	status, data = adb_run('kill-server', **kwargs)
	if not status:
		tprint('kill error:', data)
		return False, data
	status, data = adb_run('start-server', **kwargs)
	if not status:
		tprint('start error:', data)
		return False, data
	return True, data

if __name__ != '__main__': patch_import()