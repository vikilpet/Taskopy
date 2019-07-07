import sys
import time
import binascii
import socket
import select
import hashlib

class _ApiRos:
	"Routeros api"
	def __init__(self, sk, pri:bool=True):
		''' pri - print to console
		'''
		self.sk = sk
		self.currenttag = 0
		self.pri = pri

	def login(self, username, pwd):
		for repl, attrs in self.talk([
			"/login", "=name=" + username
			, "=password=" + pwd
		]):
			if repl == '!trap':
				return False
			elif '=ret' in attrs.keys():
				chal = binascii.unhexlify((attrs['=ret']).encode(sys.stdout.encoding))
				md = hashlib.md5()
				md.update(b'\x00')
				md.update(pwd.encode(sys.stdout.encoding))
				md.update(chal)
				for repl2, attrs2 in self.talk([
					"/login"
					, "=name=" + username
					, "=response=00" + binascii.hexlify(md.digest()).decode(sys.stdout.encoding)
				]):
					if repl2 == '!trap':
						return False
		return True

	def talk(self, words):
		if self.writeSentence(words) == 0: return
		r = []
		while 1:
			i = self.readSentence();
			if len(i) == 0: continue
			reply = i[0]
			attrs = {}
			for w in i[1:]:
				j = w.find('=', 1)
				if (j == -1):
					attrs[w] = ''
				else:
					attrs[w[:j]] = w[j+1:]
			r.append((reply, attrs))
			if reply == '!done': return r

	def writeSentence(self, words):
		ret = 0
		for w in words:
			self.writeWord(w)
			ret += 1
		self.writeWord('')
		return ret

	def readSentence(self):
		r = []
		while 1:
			w = self.readWord()
			if w == '': return r
			r.append(w)

	def writeWord(self, w):
		if self.pri: print(("<<< " + w))
		self.writeLen(len(w))
		self.writeStr(w)

	def readWord(self):
		ret = self.readStr(self.readLen())
		if self.pri: print((">>> " + ret))
		return ret

	def writeLen(self, l):
		if l < 0x80:
			self.writeByte((l).to_bytes(1, sys.byteorder))
		elif l < 0x4000:
			l |= 0x8000
			tmp = (l >> 8) & 0xFF
			self.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
			self.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
		elif l < 0x200000:
			l |= 0xC00000
			self.writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
			self.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
			self.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
		elif l < 0x10000000:
			l |= 0xE0000000
			self.writeByte(((l >> 24) & 0xFF).to_bytes(1, sys.byteorder))
			self.writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
			self.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
			self.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
		else:
			self.writeByte((0xF0).to_bytes(1, sys.byteorder))
			self.writeByte(((l >> 24) & 0xFF).to_bytes(1, sys.byteorder))
			self.writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
			self.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
			self.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))

	def readLen(self):
		c = ord(self.readStr(1))
		if (c & 0x80) == 0x00:
			pass
		elif (c & 0xC0) == 0x80:
			c &= ~0xC0
			c <<= 8
			c += ord(self.readStr(1))
		elif (c & 0xE0) == 0xC0:
			c &= ~0xE0
			c <<= 8
			c += ord(self.readStr(1))
			c <<= 8
			c += ord(self.readStr(1))
		elif (c & 0xF0) == 0xE0:
			c &= ~0xF0
			c <<= 8
			c += ord(self.readStr(1))
			c <<= 8
			c += ord(self.readStr(1))
			c <<= 8
			c += ord(self.readStr(1))
		elif (c & 0xF8) == 0xF0:
			c = ord(self.readStr(1))
			c <<= 8
			c += ord(self.readStr(1))
			c <<= 8
			c += ord(self.readStr(1))
			c <<= 8
			c += ord(self.readStr(1))
		return c

	def writeStr(self, str):
		n = 0;
		while n < len(str):
			r = self.sk.send(bytes(str[n:], 'UTF-8'))
			if r == 0: raise RuntimeError("connection closed by remote end")
			n += r

	def writeByte(self, str):
		n = 0;
		while n < len(str):
			r = self.sk.send(str[n:])
			if r == 0: raise RuntimeError("connection closed by remote end")
			n += r

	def readStr(self, length):
		ret = ''
		while len(ret) < length:
			s = self.sk.recv(length - len(ret))
			if s == b'': raise RuntimeError("connection closed by remote end")
			if s >= (128).to_bytes(1, "big") :
				return s
			ret += s.decode(sys.stdout.encoding, "replace")
		return ret

def routeros_send(
	cmd:str
	, device_ip:str=None
	, device_port:str='8728'
	, device_user:str='admin'
	, device_pwd:str=''
	, pri:bool=False
):
	''' Send command 'cmd' through api.
		cmd - list of strings (single command) or list
		of lists (many commands)
		Return True, None on success or False, 'error'
	'''
	soc = None
	for res in socket.getaddrinfo(
		device_ip
		, device_port
		, socket.AF_UNSPEC
		, socket.SOCK_STREAM
	):
		af, socktype, proto, canonname, sa = res
		try:
			 soc = socket.socket(af, socktype, proto)
		except socket.error:
			soc = None
			continue
		try:
			soc.connect(sa)
		except socket.error:
			soc.close()
			soc = None
			continue
		break
	
	if soc is None:
		print ('Could not open socket')
		return False, 'Could not open socket'
	try:
		apiros = _ApiRos(soc, pri=pri)
		apiros.login(device_user, device_pwd)
		if type(cmd[0]) == list:
			for c in cmd: apiros.talk(c)
		else:
			apiros.talk(cmd)
	except Exception as e:
		return False, repr(e)[:200]
	return True, None

def routeros_query(
	query:list
	, device_ip:str=None
	, device_port:str='8728'
	, device_user:str='admin'
	, device_pwd:str=''
	, pri:bool=False
):
	''' Send query and return True, data = list of dictionaries
		or False, 'error'
		query - list with commands as string.
		Example:
		query=[
			'/ip/firewall/address-list/print'
			, '?list=my_list'
		]
	'''
	soc = None
	for res in socket.getaddrinfo(
		device_ip
		, device_port
		, socket.AF_UNSPEC
		, socket.SOCK_STREAM
	):
		af, socktype, proto, canonname, sa = res
		try:
			soc = socket.socket(af, socktype, proto)
		except socket.error:
			soc = None
			continue
		try:
			soc.connect(sa)
		except socket.error:
			soc.close()
			soc = None
			continue
		break

	if soc is None:
		print ('Could not open socket')
		return False, 'Could not open socket'

	try:
		apiros = _ApiRos(soc, pri=pri)
		apiros.login(device_user, device_pwd)
		api_data = apiros.talk(query)

		
		#

		if len(api_data) > 1:
			if api_data[0][0] == '!trap':
				return False, 'bad query'
			else:
				return True, [t[1] for t in api_data[:-1]]
		else:
			return True, []
	except Exception as e:
		return False, repr(e)[:200]
	return False, 'something went wrong'
