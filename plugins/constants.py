import win32con
from .tools import patch_import
WA_PLAYING = 'playing'
WA_PAUSED = 'paused'
WA_STOPPED = 'stopped'
WA_FULLPATH = r'C:\Program Files (x86)\Winamp\winamp.exe'
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
TDCBF_OK_BUTTON = 1
TDCBF_YES_BUTTON = 2
TDCBF_NO_BUTTON = 4
TDCBF_CANCEL_BUTTON = 8
TDCBF_RETRY_BUTTON = 16
TDCBF_CLOSE_BUTTON = 32
TD_ICON_BLANK = 100
TD_ICON_WARNING = 101
TD_ICON_QUESTION = 102
TD_ICON_ERROR = 103
TD_ICON_INFORMATION = 104
TD_ICON_BLANK_AGAIN = 105
TD_ICON_SHIELD = 106
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
WINDOW_MINIMIZED = win32con.SW_SHOWMINNOACTIVE
WINDOW_MAXIMIZED = win32con.SW_SHOWMAXIMIZED
WINDOW_HIDDEN = win32con.SW_HIDE
DATE_FORMAT = '%A, %d %B %Y %H:%M:%S.%f'

if __name__ != '__main__': patch_import()