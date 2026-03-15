from plugins.tools import *
from plugins.plugin_filesystem import *

r'''
The difference between *push* and *pull* tactics:

- **push** -- triggers on file change event.
- **pull** -- try to read a new line. If it succeeds, try to read the next one.

You should test for yourself that which option is best for you.  

Usage in the *crontab*:

	def examples__log_watchdog_push(
		on_file_change=r'c:\my_file.log'
		, data:tuple=()
	):
		log_watchdog_push(
			log_file=on_file_change
			, data=data
			, callback:Callable=log_watchdog_callback_demo
		)


	def examples__log_watchdog_poll_start():
		log_watchdog_poll(
			log_file=r'c:\my_file_2.log'
			, callback:Callable=log_watchdog_callback_demo
		)
	
	def examples__log_watchdog_stop(on_exit=True):
		log_watchdog_poll_stop(r'c:\my_file_2.log')

'''

def log_watchdog_callback_demo(new_line:str)->bool:
	r'''
	Example of a `callback`.
	We should return `True` to signal that the data has been successfully
	processed and we can move on.  
	'''
	tprint('new line(s):', str_indent(new_line))
	return True

def log_watchdog_push(
	log_file:str
	, callback:Callable=log_watchdog_callback_demo
	, data:tuple=()
	, is_debug:bool=False
):
	r'''
	To use with *on_file_change* event.  
	*log_file* - a file to watch.  
	*callback* - a function that fetches new lines from a file.
	The function must accept *str* and return *bool* -- *True*
	on successful processing of new lines.  
	'''
	if is_debug: tprint(data[1])
	var_name = ('log_watchdog', log_file)
	prev_pos:int = var_get(var_name, default=0, as_literal=True)
	cur_size = file_size(log_file)
	if not prev_pos:
		dev_print('first check')
		var_set(var_name, cur_size)
		return
	if prev_pos > cur_size:
		dev_print('the file has been truncated')
		var_set(var_name, cur_size)
		return
	with open(log_file) as hnd:
		hnd.seek(prev_pos)
		for line in hnd.read().splitlines():
			status, data = safe(callback)(line)
			if not status:
				if is_debug: tprint('callback exception:' + str_indent(data))
				return
			assert isinstance(data, bool), 'callback must return bool'
			new_pos = hnd.tell()
			if is_debug:
				tprint(f'{prev_pos=}, {new_pos=}, {(new_pos - prev_pos)=}')
				tprint('line:', str_short(line, 80))
			if data: var_set(var_name, new_pos)

def log_watchdog_poll(
	log_file:str
	, callback:Callable=log_watchdog_callback_demo
	, poll_timeout:str='1 sec'
	, fail_timeout:str='11 sec'
	, empty_threshold:int=61
):
	r'''
	It's just waiting for new lines.  
	*log_file* - a file for watch.  
	*callback* - a function that processes a new line from the file.
	The function must accept a *str* with a new line and
	must return *bool* -- `True` on successful processing of the new line
	or `False` on error so that `log_watchdog_poll` will not move further.  
	*empty_threshold* - after how many empty lines should you check whether
	the file was truncated?
	'''
	fname = file_name(log_file)
	var_name = ('log_watchdog', log_file)
	flag_var_name = f'log_watchdog {log_file}'
	prev_pos:int = var_get(var_name, default=0, as_literal=True)
	cur_size = file_size(log_file)
	if not prev_pos:
		dev_print('new file:', fname)
		var_set(var_name, cur_size)
	if prev_pos > cur_size:
		dev_print('the file has been truncated before polling:', fname)
		var_set(var_name, '0')
		prev_pos = 0
	empty_count:int = 0
	gdic[flag_var_name] = True
	with open(log_file) as hnd:
		hnd.seek(prev_pos)
		while gdic[flag_var_name] == True:
			try:
				line = hnd.readline()
			except PermissionError:
				dev_print('permission error:', fname)
				gdic[flag_var_name] = False
				break
			if not line:
				empty_count += 1
				if empty_count < empty_threshold:
					time_sleep(poll_timeout)
					continue
				else:
					empty_count = 0
					cur_size = os.fstat(hnd.fileno()).st_size
					if cur_size < prev_pos:
						dev_print('the file has been truncated during polling:'
						, fname)
						var_set(var_name, '0')
						gdic[flag_var_name] = False
						break
				continue
			status:bool = False
			data:bool = False
			while gdic[flag_var_name] == True:
				status, data = safe(callback)(line)
				if not status:
					tprint('callback exception:', str_indent(data))
					time_sleep(fail_timeout)
					continue
				assert isinstance(data, bool), 'callback must return bool'
				if data: break
				time_sleep(fail_timeout)
			new_pos = hnd.tell()
			var_set(var_name, new_pos)
			prev_pos = new_pos


def log_watchdog_poll_stop(log_file:str):
	if gdic.get(f'log_watchdog {log_file}') is None:
		msg_err(f'No flag for file: «{log_file}»'
		, 'Log watchdog poll stop')
		return
	gdic[f'log_watchdog {log_file}'] = False
