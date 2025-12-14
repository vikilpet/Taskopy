import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
comctl32 = ctypes.WinDLL('comctl32', use_last_error=True)

def get_last_error()->str:
	r'''
	Return Windows last error as: 'Message (code)'  
	Example: 'Invalid window handle (1400)'  

		asrt( bmark(get_last_error), 660 )

	'''
	code = ctypes.get_last_error()
	if code == 0: return ''
	message = ctypes.FormatError(code).rstrip().rstrip('.')
	return f'{message} ({code})'
