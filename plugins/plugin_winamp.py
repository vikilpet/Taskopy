import win32api
import win32gui
from .tools import msgbox

WM_COMMAND = 0x0111
WM_USER = 0x400

def winamp_command(par1:int, par2:int, par3:int):
	h = win32gui.FindWindow('Winamp v1.x', None)
	if h:
		return win32api.SendMessage(h, par1, par2, par3)
	else:
		msgbox('Winamp not found')
		return 0

def winamp_pause():
	winamp_command(WM_COMMAND, 40046, 0)

def winamp_play():
	winamp_command(WM_COMMAND, 40045, 0)

def winamp_stop():
	winamp_command(WM_COMMAND, 40047, 0)

def winamp_status()->str:
	''' Playing, paused, stopped
	'''
	status = winamp_command(WM_USER, 0, 104)
	if status == 1:
		return 'playing'
	elif status == 3:
		return 'paused'
	elif status == 0:
		return 'stopped'

def winamp_track_title(clean:bool=True)->str:
	t = win32gui.GetWindowText(win32gui.FindWindow('Winamp v1.x', None))
	if clean:
		t = t.replace(' [Stopped]', '').replace(' [Paused]', '').replace(' - Winamp', '')
		t = t[t.find(' ') + 1:]
	return t

def winamp_track_length()->str:
	''' Return length of current track in 'mm:ss' format
	'''
	l = winamp_command(WM_USER, 1, 105)
	if l > 0:
		r = '%02d:%02d' % divmod(l, 60)
	else:
		r = 'no track?'
	return r

def winamp_notification():
	''' Show notification popup of modern skin.
	'''
	winamp_command(WM_USER, 0, 632)

def winamp_track_info(sep:str='   ')->str:
	h = win32gui.FindWindow('Winamp v1.x', None)
	if not h: return 'Winamp not found'
	samplerate = win32api.SendMessage(h, WM_USER, 0, 126)
	bitrate = win32api.SendMessage(h, WM_USER, 1, 126)
	channels = win32api.SendMessage(h, WM_USER, 2, 126)
	return f'{samplerate}kHz{sep}{bitrate}kbps{sep}{channels}ch'






