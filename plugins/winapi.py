import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
comctl32 = ctypes.WinDLL('comctl32', use_last_error=True)
import ctypes
from ctypes import wintypes


class OVERLAPPED(ctypes.Structure):
	_fields_ = [
		('Internal', wintypes.LPVOID),
		('InternalHigh', wintypes.LPVOID),
		('Offset', wintypes.DWORD),
		('OffsetHigh', wintypes.DWORD),
		('Pointer', wintypes.LPVOID),
		('hEvent', wintypes.HANDLE)
	]

def _errcheck_bool(value, func, args):
	if not value:
		raise ctypes.WinError()
	return args

CancelIoEx = kernel32.CancelIoEx
CancelIoEx.restype = wintypes.BOOL
CancelIoEx.errcheck = _errcheck_bool
CancelIoEx.argtypes = ( wintypes.HANDLE, ctypes.POINTER(OVERLAPPED) )
class KBDLLHOOKSTRUCT(ctypes.Structure):
	_fields_ = [
		('vkCode', wintypes.DWORD),
		('scanCode', wintypes.DWORD),
		('flags', wintypes.DWORD),
		('time', wintypes.DWORD),
		('dwExtraInfo', ctypes.POINTER(wintypes.ULONG))
	]
LowLevelHookProc = ctypes.WINFUNCTYPE(
	wintypes.LPARAM,
	ctypes.c_int,
	wintypes.WPARAM,
	wintypes.LPARAM
)

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
