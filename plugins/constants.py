import win32con
CALLER_HOTKEY = 'hotkey'
CALLER_HTTP = 'http'
CALLER_MENU = 'menu'
CALLER_SCHEDULER = 'scheduler'
CALLER_BROWSER = 'browser'
CALLER_LOAD = 'load'
CALLER_IDLE = 'idle'
CALLER_LEFT_CLICK = 'left_click'
CALLER_STARTUP = 'startup'
CALLER_SYS_STARTUP = 'sys_startup'
CALLER_EVENT = 'event'
CALLER_EXIT = 'exit'
CALLER_FILE_CHANGE = 'file_change'
CALLER_DIR_CHANGE = 'dir_change'
CALLER_CMDLINE = 'cmd_line'
TDCBF_OK_BUTTON = 1
TDCBF_YES_BUTTON = 2
TDCBF_NO_BUTTON = 4
TDCBF_CANCEL_BUTTON = 8
TDCBF_RETRY_BUTTON = 16
TDCBF_CLOSE_BUTTON = 32
TD_ICON_BLANK = 0
TD_ICON_WARNING = 84
TD_ICON_QUESTION = 99
TD_ICON_ERROR = 98
TD_ICON_INFORMATION = 81
TD_ICON_SHIELD = 78
TD_ICON_CROSS = 89
TD_ICON_SHIELD_BROWN = 65527
TD_ICON_SHIELD_OK = 65528
TD_ICON_SHIELD_ERROR = 65529
TD_ICON_SHIELD_WARNING = 65530
TD_ICON_SHIELD_BLUE = 65531
TDF_ENABLE_HYPERLINKS = 1
TDF_USE_HICON_MAIN = 2
TDF_USE_HICON_FOOTER = 4
TDF_ALLOW_DIALOG_CANCELLATION = 8
TDF_USE_COMMAND_LINKS = 16
TDF_USE_COMMAND_LINKS_NO_ICON = 32
TDF_EXPAND_FOOTER_AREA = 64
TDF_EXPANDED_BY_DEFAULT = 128
TDF_VERIFICATION_FLAG_CHECKED = 256
TDF_SHOW_PROGRESS_BAR = 512
TDF_SHOW_MARQUEE_PROGRESS_BAR = 1024
TDF_CALLBACK_TIMER = 2048
TDF_POSITION_RELATIVE_TO_WINDOW = 4096
TDF_RTL_LAYOUT = 8192
TDF_NO_DEFAULT_RADIO_BUTTON = 16384
TDF_CAN_BE_MINIMIZED = 32768
DL_CANCEL = win32con.IDCANCEL
DL_OK = win32con.IDOK
DL_TIMEOUT = 0
WIN_MINIMIZED = win32con.SW_SHOWMINNOACTIVE
WIN_MAXIMIZED = win32con.SW_SHOWMAXIMIZED
WIN_HIDDEN = win32con.SW_HIDE
DATE_FORMAT = '%A, %d %B %Y %H:%M:%S.%f'
DATE_STR_ISO_MCS = '%Y-%m-%d %H:%M:%S.%f'
DATE_STR_ISO = '%Y-%m-%d %H:%M:%S'
DATE_STR_ISO_FILE = '%Y-%m-%d %H-%M-%S'
DATE_STR_FILE = '%Y-%m-%d_%H-%M-%S'
RE_DATE_STR_FILE = r'\d\d\d\d-\d\d-\d\d_\d\d-\d\d_\d\d'
DATE_STR_FILE_SHORT = '%Y-%m-%d'
RE_DATE_STR_FILE_SHORT = r'\d\d\d\d-\d\d-\d\d'
DATE_STR_HUMAN = '%Y.%m.%d %H:%M:%S'
RE_DATE_STR_HUMAN = r'\d\d\d\d\.\d\d\.\d\d \d\d:\d\d:\d\d'
DATE_STR_HUMAN_SHORT = '%Y.%m.%d'
RE_DATE_STR_HUMAN_SHORT = r'\d\d\d\d\.\d\d\.\d\d'
_APP_FAVICON = 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAktJREFUeNqUU0toE1EUPW+SNJlJrUlrqiFGaIOfmhSCoFVEodRaFxUEoQrizo0IXSi4LgXFVUEXLjQRPxt3IipSUGlFg0X7QzDG0jZqbBqTGGoy5p/xvqEJMW0VL3Nn5t13z5l775zHkv5TqDF3JCX167XFHlFbaOKBfElIlxQ2a6zLD2uYcpdCgXIyqyIwpHK625R0gtFCzumwkDRCKygwGTIwi1k1SeGXwgYYUwarCcRsQTNCX90zGbbg3lQbAjHzH2VtbkjhyNYgju6YRzDREPaMO7dcOfy6oFVZFXaVgx98cMAz7sJqFvpZr+69+mxDRJasibR+iML9vIJ2Kmt6Jm5iF54eBPWKtcyoy0OqKyAqi8vdYL9AtzMEYY8/tlbA1N8KsNsaxbXeUZpJqTI/XgEn6OGrqUWLGt0gpeE99gzO5ngF3O34goHON7jx1oUwDbbKujhBK80A1JMaif0S8TJow+VuH3bbIuhsCeFcxzSGfLswFtpUW5hFq86wJnpncicEauPigXdcAxgc6cDEQvOqc+EEs5TcZjJk8SNtKP9r3Jpw4lGgBbmiBksZ/VpzjfEWnvM318b4it2oLP0NzG2YE1zn6urdPg+G/7Ic+SVO4C+WhJt86sedM/9EORqX0CRl+Ov5J6cf+qul7CM1ul/M2XH//TZ8I+VVW6OYwSHHV5xsDyjfZWnMvj65r/Yw1RdKgpeE0scXiykjIilRPUxmAlvXyeUW8+Rnyb21BGXby9VJ2ugCU+zLsQSBP9FzlNxDPldO/i3AAPuE3dwUbVLNAAAAAElFTkSuQmCC'
MONITOR_ON = -1
MONITOR_OFF = 2
MONITOR_STANDBY = 1
MIME_TEXT = 'text/plain; charset=utf-8'
MIME_HTML = 'text/html; charset=utf-8'
MIME_JSON = 'application/json'
MIME_BINARY = 'application/octet-stream'
FILE_CREATED = 'created'
FILE_DELETED = 'deleted'
FILE_UPDATED = 'updated'
FILE_RENAMED_FROM = 'renamed_from'
FILE_RENAMED_TO = 'renamed_to'
# on_dir_change, on_file_change actions:
FILE_ACTIONS = {
	1 : FILE_CREATED
	, 2 : FILE_DELETED
	, 3 : FILE_UPDATED
	, 4 : FILE_RENAMED_FROM
	, 5 : FILE_RENAMED_TO
}
FILE_NOTIFY_CHANGE_LAST_ACCESS = 32
FILE_NOTIFY_CHANGE_CREATION = 64
FILE_NOTIFY_CHANGE_SIZE = win32con.FILE_NOTIFY_CHANGE_SIZE
FILE_NOTIFY_CHANGE_FILE_NAME = win32con.FILE_NOTIFY_CHANGE_FILE_NAME
FILE_NOTIFY_CHANGE_DIR_NAME = win32con.FILE_NOTIFY_CHANGE_DIR_NAME
FILE_NOTIFY_CHANGE_ATTRIBUTES = win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES
FILE_NOTIFY_CHANGE_LAST_WRITE = win32con.FILE_NOTIFY_CHANGE_LAST_WRITE
FILE_NOTIFY_CHANGE_SECURITY = win32con.FILE_NOTIFY_CHANGE_SECURITY
# For displaying small messages:
HTML_MSG = r'''
<!doctype html>
<html>
	<head>
		<meta charset="utf-8">
		<title>t</title>
		<style>
			html, body {{
				height: 100%;
				font-size: calc((5vw + 5vh)/2);
				overflow-wrap: anywhere;
				margin: 0 1vw 0 1vw;
			}}
			* {{
				font-size: calc((5vw + 5vh)/2);
			}}
			.container {{
				height: 100%;
				display: flex;
				justify-content: center;
				flex-direction: column;
				align-items: center;
				text-align: center;
				gap: 0;
			}}
		</style>
		<script></script>
	</head>
	<body>
		<div class='container'>
			{}
		</div>
	</body>
</html>
'''.replace('\t', '').replace('\n', '')
# Empty tags: *title*, *style*, *div* to
# ease optional replacement:
# tcon.HTML_BASIC.replace('>t<', '>My Title<')
HTML_BASIC = r'''
<!doctype html>
<html>
	<head>
		<meta charset="utf-8">
		<title>t</title>
		<style></style>
		<script></script>
	</head>
	<body>
		{}
	</body>
</html>
'''.replace('\t', '').replace('\n', '')
HTML_CENTER = r'''
<!doctype html>
<html>
	<head>
		<meta charset="utf-8">
		<title>t</title>
		<script></script>
		<style>
			* {{
				font-family: Verdana, Arial, sans-serif;
				font-size: calc((2vw + 2vh)/2);
			}}
			table {{
				border: 1px solid #ccc;
			}}
		</style>
	</head>
	<body>
		<div style="display: flex; justify-content: center;">
			<div style="text-align: center;">
				{}
			</div>
		</div>
	</body>
</html>
'''.replace('\t', '').replace('\n', '')

if __name__ != '__main__':
	try:
		from .tools import patch_import
		patch_import()
	except ImportError:
		print('import of patch_import failed')
