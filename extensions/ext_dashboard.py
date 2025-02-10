from plugins.tools import *
from plugins.plugin_filesystem import *
from plugins.plugin_network import *

r'''
Create HTML dashboard with optional actions.  

Don't forget to download the *ext_dashboard.html* and place it
in Taskopy root directory.  

Use in *crontab*:

	from ext_dashboard import dash_page
	def _dash_src()->dict:
		return {
			'time': '🕔 ' + time_str(template=tcon.DATE_STR_HUMAN)
			, 'msg': 'It works!'
		}
		
	def dashboard(data:DataHTTPReq, http=True, result=True, log=False
	, menu=False, err_threshold=10):
		return dash_page(
			source=_dash_src
			, data=data
			, actions={
				'msg': lambda: 'Definitely!'
				, 'status': lambda: '😊'
			}
		)


Open the URL on your phone: http://Your.PC.IP.Address:8275/dashboard

Your phone's IP address must fall under the *white_list*
parameter in the *settings.ini* file (or in *http_white_list* of the task)
otherwise you will get 403 error.

'''
_DASH_HTML:str = ''
_DASH_HTML_FILE:str = path_get((app_dir(), 'ext_dashboard.html'))

def dash_page(source:Callable, actions:dict={}, title:str='Dashboard'
, max_status_len:int=60, http:str='^dashboard$', data:DataHTTPReq=None)->str:
	r'''
	Returns a string wiht HTML page.  
	'''
	global _DASH_HTML
	if not data.params:
		if not _DASH_HTML: _DASH_HTML = file_read(_DASH_HTML_FILE)
		page = _DASH_HTML.replace('%title%', title)
		return page
	if 'd' in data.params:
		return json.dumps(source())
	if 'a' in data.params:
		if not (action := actions.get(data.params['a'])):
			return '?'
		status, data = safe(action)()
		if status:
			return 'ok' if data == None else str_short(data, max_status_len)
		# There is an exception:
		tprint('action exception:', str_indent(data))
		return 'error: ' + str_short(data, max_status_len - 7)

@task_add
def dash_reload_html(on_file_change=_DASH_HTML_FILE, menu=False, log=False):
	global _DASH_HTML
	_DASH_HTML = ''
