from plugins.tools import *
from plugins.plugin_filesystem import *

r'''
The difference between *push* and *pull* tactics:

- **push** -- triggers on file change event.
- **pull** -- try to read a new line. If it succeeds, try to read the next one.

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
		tprint('first check')
		var_set(var_name, cur_size)
		return
	if prev_pos > cur_size:
		tprint('the file was truncated?')
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
):
	r'''
	It's just waiting for new lines.  
	*log_file* - a file for watch.  
	*callback* - a function that fetches new lines from a file.
	The function must accept *str* and return *bool* -- *True*
	on successful processing of new lines.  
	'''
	var_name = ('log_watchdog', log_file)
	flag_var_name = f'log_watchdog {log_file}'
	prev_pos:int = var_get(var_name, default=0, as_literal=True)
	cur_size = file_size(log_file)
	if not prev_pos:
		tprint('first check')
		var_set(var_name, cur_size)
	if prev_pos > cur_size:
		tprint('the file was truncated?')
		var_set(var_name, cur_size)
		prev_pos = cur_size
	gdic[flag_var_name] = True
	with open(log_file) as hnd:
		hnd.seek(prev_pos)
		while gdic[flag_var_name] == True:
			line = hnd.readline()
			if not line:
				time_sleep(poll_timeout)
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
	tprint('stop')


def log_watchdog_poll_stop(log_file:str):
	gdic[f'log_watchdog {log_file}'] = False
