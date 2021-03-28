import win32api
import win32gui
import win32con
from .tools import dialog, patch_import
from .plugin_process import app_start
import plugins.constants as tcon

def winamp_command(par1:int, par2:int, par3:int):
	h = win32gui.FindWindow('Winamp v1.x', None)
	if h:
		return win32api.SendMessage(h, par1, par2, par3)
	else:
		if dialog(
			'Winamp not found. Open?'
			, content=f'WA_FULLPATH={tcon.WA_FULLPATH}'
			, buttons=['Open', 'Cancel']
		) == 1000:
			app_start(tcon.WA_FULLPATH)
		return 0

def winamp_pause(): winamp_command( win32con.WM_COMMAND, 40046, 0)
def winamp_play(): winamp_command(win32con.WM_COMMAND, 40045, 0)
def winamp_stop(): winamp_command(win32con.WM_COMMAND, 40047, 0)
def winamp_previous(): winamp_command(win32con.WM_COMMAND, 40044, 0)
def winamp_next(): winamp_command(win32con.WM_COMMAND, 40048, 0)
def winamp_fast_forward(): winamp_command(win32con.WM_COMMAND, 40148, 0)
def winamp_fast_rewind(): winamp_command(win32con.WM_COMMAND, 40144, 0)
def winamp_toggle_main_window(): winamp_command(win32con.WM_COMMAND, 40258, 0)
def winamp_toggle_media_library(): winamp_command(win32con.WM_COMMAND, 40379, 0)
def winamp_toggle_always_on_top(): winamp_command(win32con.WM_COMMAND, 40019, 0)
def winamp_close(): winamp_command(win32con.WM_COMMAND, 40001, 0)
def winamp_volume_set(volume:int): winamp_command(win32con.WM_USER, volume, 122)

def winamp_status()->str:
	''' -> 'playing', 'paused', 'stopped'
	'''
	status = winamp_command(win32con.WM_USER, 0, 104)
	if status == 1:
		return tcon.WA_PLAYING
	elif status == 3:
		return tcon.WA_PAUSED
	elif status == 0:
		return tcon.WA_STOPPED

def winamp_track_title(clean:bool=True)->str:
	t = win32gui.GetWindowText( win32gui.FindWindow('Winamp v1.x', None) )
	if clean:
		t = t.replace(' [Stopped]', '').replace(' [Paused]', '') \
			.replace(' - Winamp', '')
		t = t[t.find(' ') + 1:]
	return t

def winamp_track_length()->str:
	''' Return length of current track in 'mm:ss' format
	'''
	l = winamp_command(win32con.WM_USER, 1, 105)
	if l > 0:
		r = '%02d:%02d' % divmod(l, 60)
	else:
		r = 'no track?'
	return r

def winamp_notification():
	''' Show notification popup of modern skin.
	'''
	winamp_command(win32con.WM_USER, 0, 632)

def winamp_track_info(sep:str='   ')->str:
	h = win32gui.FindWindow('Winamp v1.x', None)
	if not h: return 'Winamp not found'
	samplerate = win32api.SendMessage(h, win32con.WM_USER, 0, 126)
	bitrate = win32api.SendMessage(h, win32con.WM_USER, 1, 126)
	channels = win32api.SendMessage(h, win32con.WM_USER, 2, 126)
	return f'{samplerate}kHz{sep}{bitrate}kbps{sep}{channels}ch'

if __name__ != '__main__': patch_import()
