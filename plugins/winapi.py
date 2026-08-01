import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)
ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
comctl32 = ctypes.WinDLL('comctl32', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)
ole32 = ctypes.WinDLL('ole32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)

HICON = wintypes.HICON
UINT = wintypes.UINT
ULONG_PTR = ctypes.c_size_t
LONG_PTR  = ctypes.c_ssize_t
LRESULT   = LONG_PTR


class GUID(ctypes.Structure):
	_fields_ = [
		('Data1', ctypes.c_ulong),
		('Data2', ctypes.c_ushort),
		('Data3', ctypes.c_ushort),
		('Data4', ctypes.c_ubyte * 8),
	]

	def __init__(self, s: str = None):
		super().__init__()
		if s is not None:
			hr = ole32.CLSIDFromString(wintypes.LPCWSTR(s), ctypes.byref(self))
			if hr != 0:
				raise OSError(f'CLSIDFromString({s!r}) failed: 0x{hr & 0xFFFFFFFF:08X}')


ole32.CLSIDFromString.restype  = ctypes.HRESULT
ole32.CLSIDFromString.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(GUID)]
ole32.CoInitializeEx.restype  = ctypes.HRESULT
ole32.CoInitializeEx.argtypes = [wintypes.LPVOID, wintypes.DWORD]
ole32.CoUninitialize.restype  = None
ole32.CoUninitialize.argtypes = []
ole32.CoCreateInstance.restype  = ctypes.HRESULT
ole32.CoCreateInstance.argtypes = [
	ctypes.POINTER(GUID),               # rclsid
	wintypes.LPVOID,                    # pUnkOuter
	wintypes.DWORD,                     # dwClsContext
	ctypes.POINTER(GUID),               # riid
	ctypes.POINTER(wintypes.LPVOID),    # ppv
]

CLSCTX_ALL               = 0x17
COINIT_APARTMENTTHREADED = 0x2
COINIT_MULTITHREADED     = 0x0
def com_vcall(ptr, slot, restype, argtypes, *args):
	"""
	Invoke vtable[slot] of the COM object behind `ptr` (a c_void_p).
	Slots 0/1/2 are IUnknown::QueryInterface / AddRef / Release.
	"""
	vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
	fn   = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtbl[slot])
	return fn(ptr, *args)

def com_release(ptr):
	"""IUnknown::Release — safe to call with a NULL pointer."""
	if ptr:
		com_vcall(ptr, 2, ctypes.c_uint, [])


class _OVERLAPPED_UNION(ctypes.Structure):
	_fields_ = [
		('Offset', wintypes.DWORD),
		('OffsetHigh', wintypes.DWORD),
	]


class OVERLAPPED(ctypes.Structure):
	_anonymous_ = ('_u',)    # makes Offset/OffsetHigh/Pointer accessible directly
	_fields_ = [
		('Internal', ULONG_PTR),
		('InternalHigh', ULONG_PTR),
		('_u', _OVERLAPPED_UNION),         # union: 8 bytes on x64
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
		('dwExtraInfo', ULONG_PTR),
	]
TH32CS_SNAPPROCESS                = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x00001000
PROCESS_VM_READ                   = 0x00000010
TOKEN_QUERY                       = 0x00000008
PROCESSBASICINFO_CLASS = 0
PROCESSWOW64_CLASS     = 26
PEB_PROCESS_PARAMETERS_OFFSET_32 = 0x10
PEB_PROCESS_PARAMETERS_OFFSET_64 = 0x20
PEB_COMMANDLINE_OFFSET_32         = 0x40
PEB_COMMANDLINE_OFFSET_64         = 0x70
INVALID_HANDLE_VALUE = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1


class PROCESSENTRY32W(ctypes.Structure):
	_fields_ = [
		('dwSize',              wintypes.DWORD),
		('cntUsage',            wintypes.DWORD),
		('th32ProcessID',       wintypes.DWORD),
		('th32DefaultHeapID',   ULONG_PTR),
		('th32ModuleID',        wintypes.DWORD),
		('cntThreads',          wintypes.DWORD),
		('th32ParentProcessID', wintypes.DWORD),
		('pcPriClassBase',      wintypes.LONG),
		('dwFlags',             wintypes.DWORD),
		('szExeFile',           wintypes.WCHAR * 260),
	]


class UNICODE_STRING32(ctypes.Structure):
	_fields_ = [
		('Length',        wintypes.USHORT),
		('MaximumLength', wintypes.USHORT),
		('Buffer',        ctypes.c_uint32),
	]


class UNICODE_STRING64(ctypes.Structure):
	_fields_ = [
		('Length',        wintypes.USHORT),
		('MaximumLength', wintypes.USHORT),
		('Buffer',        ctypes.c_uint64),
	]


class PROCESS_BASIC_INFORMATION32(ctypes.Structure):
	_fields_ = [
		('ExitStatus',     ctypes.c_uint32),
		('PebBaseAddress', ctypes.c_uint32),
		('AffinityMask',   ctypes.c_uint32),
		('BasePriority',   ctypes.c_uint32),
		('UniqueProcId',   ctypes.c_uint32),
		('InheritedPid',   ctypes.c_uint32),
	]


class PROCESS_BASIC_INFORMATION64(ctypes.Structure):
	_fields_ = [
		('ExitStatus',     ctypes.c_uint64),
		('PebBaseAddress', ctypes.c_uint64),
		('AffinityMask',   ctypes.c_uint64),
		('BasePriority',   ctypes.c_uint64),
		('UniqueProcId',   ctypes.c_uint64),
		('InheritedPid',   ctypes.c_uint64),
	]
kernel32.CreateToolhelp32Snapshot.restype  = wintypes.HANDLE
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.Process32FirstW.restype  = wintypes.BOOL
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype  = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.OpenProcess.restype  = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.ReadProcessMemory.restype  = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [
	wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
	ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
]
kernel32.CloseHandle.restype  = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
ntdll.NtQueryInformationProcess.restype  = wintypes.LONG
ntdll.NtQueryInformationProcess.argtypes = [
	wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
	wintypes.ULONG, ctypes.POINTER(wintypes.ULONG),
]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
HOOKPROC = ctypes.WINFUNCTYPE(
	LRESULT,   # return type — 64-bit on x64!
	ctypes.c_int,       # nCode
	wintypes.WPARAM,    # wParam — 64-bit on x64!
	wintypes.LPARAM     # lParam — 64-bit on x64!
)

user32.SetWindowsHookExW.argtypes = [
	ctypes.c_int,       # idHook
	HOOKPROC,           # lpfn — the callback type
	wintypes.HMODULE,   # hMod — pointer-sized!
	wintypes.DWORD      # dwThreadId
]
user32.SetWindowsHookExW.restype = wintypes.HHOOK  # pointer-sized!
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = [
	wintypes.HHOOK,
	ctypes.c_int,
	wintypes.WPARAM,
	wintypes.LPARAM
]
user32.UnhookWindowsHookEx.restype  = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.IsIconic.restype          = wintypes.BOOL
user32.IsIconic.argtypes         = [wintypes.HWND]
user32.ShowWindow.restype        = wintypes.BOOL
user32.ShowWindow.argtypes       = [wintypes.HWND, wintypes.INT]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetForegroundWindow.argtypes = []
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, wintypes.LPDWORD]
user32.SetWindowPos.restype     = wintypes.BOOL
user32.SetWindowPos.argtypes    = [wintypes.HWND, wintypes.HWND,
								wintypes.INT, wintypes.INT,
								wintypes.INT, wintypes.INT,
								wintypes.UINT]

user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.BringWindowToTop.restype   = wintypes.BOOL
user32.BringWindowToTop.argtypes  = [wintypes.HWND]
user32.SetActiveWindow.restype    = wintypes.HWND
user32.SetActiveWindow.argtypes   = [wintypes.HWND]
user32.SetFocus.restype           = wintypes.HWND
user32.SetFocus.argtypes          = [wintypes.HWND]
user32.keybd_event.restype        = None
user32.keybd_event.argtypes       = [wintypes.BYTE, wintypes.BYTE,
                                    wintypes.DWORD, ULONG_PTR]

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
