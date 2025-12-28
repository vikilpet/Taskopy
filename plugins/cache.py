import datetime
from collections import OrderedDict
import windows_toasts as wtoasts


class LRUCache(dict):
	r'''
	Simple dict with a max size — evicts least recently used items
	'''

	def __init__(self, max_items: int = 100):
		super().__init__()
		self.max_items = max_items
		self._order = OrderedDict()

	def __getitem__(self, key):
		if key in self:
			self._order.move_to_end(key)
		return super().__getitem__(key)

	def __setitem__(self, key, value):
		if key in self:
			self._order.move_to_end(key)
		else:
			if len(self) >= self.max_items:
				oldest = next(iter(self._order))
				del self[oldest]
				del self._order[oldest]
		super().__setitem__(key, value)
		self._order[key] = None

	def get(self, key, default=None):
		if key in self:
			self._order.move_to_end(key)


is_con:bool|None = None
often:dict[str, datetime.datetime] = {}
toast_toasters:dict[str, wtoasts.WindowsToaster] = {}
toast_imgs = LRUCache(max_items=16)

