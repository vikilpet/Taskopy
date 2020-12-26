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

if __name__ != '__main__': patch_import()