import argparse
import wx

sett = {
	'win_title'			: 'Hint'
	, 'win_title_max'	: 20
	, 'win_style'		: wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR
		| wx.FRAME_TOOL_WINDOW
	, 'font_size'		: 18
	, 'font_name'		: 'Lucida Console'
	, 'back_color'		: (210, 210, 0)
}

class HintFrame(wx.Frame):
	'''' We simply derive a new class of Frame. '''
	def __init__(self, parent, text:str='', position:tuple=None):
		DRAG_AREA_SIZE = 20
		global sett
		size_w = int( len(text) * int(sett['font_size']) * 0.85 + DRAG_AREA_SIZE )
		size_h = int(sett['font_size'] * 1.7)
		title = text[:sett['win_title_max']]
		if len(text) > sett['win_title_max']: title += '...'
		wx.Frame.__init__(
			self
			, parent
			, title=sett['win_title'] + ': ' + title
			, size=(size_w, size_h)
			, style=sett['win_style']
		)
		self.control = wx.TextCtrl(
			self
			, value=text
			, size=(size_w - DRAG_AREA_SIZE, size_h)
			, style=wx.BORDER_NONE | wx.TE_READONLY | wx.TE_CENTRE
		)
		self.control.BackgroundColour = wx.Colour(sett['back_color'])
		clr = sett['back_color']
		clr = int(clr[0] * 0.9), int(clr[1] * 0.9), int(clr[2] * 0.9)
		self.BackgroundColour = wx.Colour(clr)
		self.control.Font = wx.Font(sett['font_size'], wx.MODERN
		, wx.NORMAL, wx.NORMAL, False, sett['font_name'])
		if position:
			self.SetPosition(position)
		else:
			self.Center()
		self.Bind(wx.EVT_MOTION, self.OnFrame1Motion)
		self.Bind(wx.EVT_LEFT_DOWN, self.OnFrame1LeftDown)
		self.Bind(wx.EVT_LEFT_DCLICK, self.closeWindow)
		self.lastMousePos = wx.Point(0, 0)
		self.Show()

	def OnFrame1Motion(self, event):
		if event.LeftIsDown():
			windowX = self.lastMousePos[0]
			windowY = self.lastMousePos[1]
			screenX = wx.GetMousePosition()[0]
			screenY = wx.GetMousePosition()[1]
			self.Move(wx.Point(screenX - windowX, screenY - windowY))
		event.Skip()

	def OnFrame1LeftDown(self, event):
		self.lastMousePos = event.GetPosition()
		event.Skip()
	
	def closeWindow(self, e):
		self.Destroy()

def _parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('--text', '-t', help='Hint text'
		, type=str, default='Hint')
	parser.add_argument('--position', '-p', help='Position'
		, type=str, default=None)
	parser.add_argument('--color', '-c', help='Hint color'
		, type=str, default='210_210_0')
	return parser.parse_args()

def main():
	args = _parse_args()
	position = None
	if args.position:
		position = tuple( map(int, args.position.split('_')) )
	app = wx.App(False)
	HintFrame(None, text=args.text, position=position)
	app.MainLoop()

if __name__ == '__main__': main()
