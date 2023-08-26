from plugins.tools import *
from plugins.plugin_filesystem import *
from plugins.plugin_network import *

r'''
Create HTML menu with configurable actions.  

Crontab task example:

	from ext_remote import rmt_page
	def remote_demo(data:DataHTTPReq, http=True
	, result=True, log=False, menu=False):
		return rmt_page(
			actions={
				# This action will return 'y', 'n' or 0 (timeout):
				'Dialog': lambda: dialog({'Yes': 'y', 'No': 'n'}, timeout=3)
				# Just an example of an action with an error:
				, 'Make an error': lambda: 0 / 0
				# Press a hotkey:
				, 'Pause': lambda: key_send('space')
				, 'Rewind': lambda: key_send('left')
				, 'Forward': lambda: key_send('right')
			}
			, data=data
		)

'''
_RMT_HTML:str = ''

def rmt_page(actions:dict, data:DataHTTPReq, title:str='Remote'
, status_src:Callable|None=None, max_status_len:int=60)->str:
	r'''
	Returns string wiht HTML or action result  
	*actions* -- a dictionary where keys are button captions
	and values are actions to call.  
	*status_src* -- function whose value is substituted
	into the status field. New lines via `<br>`. No more than 
	two lines.  
	'''
	global _RMT_HTML
	BUTTON_TEMPL = '''<div class='task' onclick="SendReq(this)">{capt}</div>'''
	if not data.form:
		# It's not an action request, so create a page
		if not _RMT_HTML: _RMT_HTML = html_minify(file_read('ext_remote.html'))
		buttons = ''
		for capt in actions.keys(): buttons += BUTTON_TEMPL.format(capt=capt)
		page = _RMT_HTML.replace('%title%', title).replace('%buttons%', buttons)
		status_str = time_str(tcon.DATE_STR_HUMAN)
		if status_src:
			status, data = safe(status_src)()
			if status:
				status_str = str(data)
			else:
				status_str = str(data)
		return page.replace('%status%', str_short(status_str, max_status_len))
	# It's an action. Let's perform it safely:
	status, data = safe( actions.get( data.form['action'] ) )()
	if status: return 'ok' if data == None else str_short(data, max_status_len)
	# There is an error:
	tprint(data)
	return 'error: ' + str_short(data, max_status_len - 7)

