# source: https://wiki.mikrotik.com/wiki/Manual:API_Python3

import sys
import binascii
import socket
import hashlib
from .tools import patch_import

_DEF_TIMEOUT = 180.0 # seconds

class _ApiRos:
	"Routeros api"
	def __init__(s, sk, info:bool=False):
		''' info - print routeros replies to console
		'''
		s.sk = sk
		s.currenttag = 0
		s.info = info

	def login(s, username, pwd):
		for repl, attrs in s.talk([
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
				for repl2, attrs2 in s.talk([
					"/login"
					, "=name=" + username
					, "=response=00" + binascii.hexlify(md.digest()).decode(sys.stdout.encoding)
				]):
					if repl2 == '!trap':
						return False
		return True

	def talk(s, words):
		if s.writeSentence(words) == 0: return
		r = []
		while 1:
			i = s.readSentence();
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

	def writeSentence(s, words):
		ret = 0
		for w in words:
			s.writeWord(w)
			ret += 1
		s.writeWord('')
		return ret

	def readSentence(s):
		r = []
		while 1:
			w = s.readWord()
			if w == '': return r
			r.append(w)

	def writeWord(s, w):
		if s.info: print(("<<< " + w))
		s.writeLen(len(w))
		s.writeStr(w)

	def readWord(s):
		ret = s.readStr(s.readLen())
		if s.info: print((">>> " + ret))
		return ret

	def writeLen(s, l):
		if l < 0x80:
			s.writeByte((l).to_bytes(1, sys.byteorder))
		elif l < 0x4000:
			l |= 0x8000
			tmp = (l >> 8) & 0xFF
			s.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
			s.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
		elif l < 0x200000:
			l |= 0xC00000
			s.writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
			s.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
			s.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
		elif l < 0x10000000:
			l |= 0xE0000000
			s.writeByte(((l >> 24) & 0xFF).to_bytes(1, sys.byteorder))
			s.writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
			s.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
			s.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
		else:
			s.writeByte((0xF0).to_bytes(1, sys.byteorder))
			s.writeByte(((l >> 24) & 0xFF).to_bytes(1, sys.byteorder))
			s.writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
			s.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
			s.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))

	def readLen(s):
		c = ord(s.readStr(1))
		if (c & 0x80) == 0x00:
			pass
		elif (c & 0xC0) == 0x80:
			c &= ~0xC0
			c <<= 8
			c += ord(s.readStr(1))
		elif (c & 0xE0) == 0xC0:
			c &= ~0xE0
			c <<= 8
			c += ord(s.readStr(1))
			c <<= 8
			c += ord(s.readStr(1))
		elif (c & 0xF0) == 0xE0:
			c &= ~0xF0
			c <<= 8
			c += ord(s.readStr(1))
			c <<= 8
			c += ord(s.readStr(1))
			c <<= 8
			c += ord(s.readStr(1))
		elif (c & 0xF8) == 0xF0:
			c = ord(s.readStr(1))
			c <<= 8
			c += ord(s.readStr(1))
			c <<= 8
			c += ord(s.readStr(1))
			c <<= 8
			c += ord(s.readStr(1))
		return c

	def writeStr(s, str):
		n = 0;
		while n < len(str):
			r = s.sk.send(bytes(str[n:], 'UTF-8'))
			if r == 0: raise RuntimeError("connection closed by remote end")
			n += r

	def writeByte(s, str):
		n = 0;
		while n < len(str):
			r = s.sk.send(str[n:])
			if r == 0: raise RuntimeError("connection closed by remote end")
			n += r

	def readStr(s, length):
		ret = ''
		while len(ret) < length:
			com_s = s.sk.recv(length - len(ret))
			if com_s == b'':
				raise RuntimeError('connection closed by remote end')
			if com_s >= (128).to_bytes(1, 'big') :
				return com_s
			ret += com_s.decode(sys.stdout.encoding, 'replace')
		return ret

def routeros_send(
	cmd:list
	, device_ip:str=None
	, device_port:str='8728'
	, device_user:str='admin'
	, device_pwd:str=''
	, info:bool=False
	, connect_timeout:float=_DEF_TIMEOUT
)->tuple[bool, None|str]:
	r'''
	Send command 'cmd' through api.
	*cmd* - list of strings (single command) or list
	of lists (many commands at once).
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
			soc.settimeout(connect_timeout) # seconds
		except socket.error:
			soc = None
			continue
		try:
			soc.connect(sa)
		except socket.error:
			soc.close(); soc = None
			continue
		break
	
	if soc is None:
		if info: print('routeros_send: Could not open socket')
		return False, 'Could not open socket'
	try:
		apiros = _ApiRos(soc)
		apiros.login(device_user, device_pwd)
		if isinstance(cmd[0], list):
			for c in cmd: apiros.talk(c)
		else:
			apiros.talk(cmd)
	except Exception as e:
		if info: print(f'routeros_send exception:\n{repr(e)}'
		+ f'\nat line {e.__traceback__.tb_lineno}')
		soc.close(); soc = None
		return False, repr(e)[:200]
	soc.close(); soc = None
	return True, None

def routeros_find_send(
	cmd_find:list
	, cmd_send:list
	, device_ip:str=None
	, device_port:str='8728'
	, device_user:str='admin'
	, device_pwd:str=''
	, info:bool=False
	, connect_timeout:float=_DEF_TIMEOUT
)->tuple[bool, None|str]:
	''' Find id and perform command against them.
		cmd_find - list of str to get list of id's.
			Example - find static id's in address-list:
				cmd_send=[
					'/ip/firewall/address-list/print'
					, '?list=my_list'
					, '?dynamic=false'
				]
		cmd_send - list of str with action that needs to be performed
			over found items.
			Example - remove from address-list:
				cmd_send=['/ip/firewall/address-list/remove']
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
			soc.settimeout(connect_timeout)
		except socket.error:
			soc = None
			continue
		try:
			soc.connect(sa)
		except socket.error:
			soc.close(); soc = None
			continue
		break
	
	if soc is None:
		if info: print('routeros_find_send: Could not open socket')
		return False, 'Could not open socket'
	try:
		apiros = _ApiRos(soc)
		apiros.login(device_user, device_pwd)
		api_data = apiros.talk(cmd_find)
		if api_data[0][0] == '!trap':
			if info: print(f'routeros_find_send bad query:\n{api_data}')
			soc.close(); soc = None
			return False, 'bad query'
		id_list = [tup[1]['=.id'] for tup in api_data[:-1]]
		if info: print(f'routeros_find_send: {id_list=}')
		apiros.talk(cmd_send + [f'=numbers=' + ','.join(id_list)])
	except Exception as e:
		if info: print(f'routeros_find_send exception:\n{repr(e)}'
		+ f'\nat line {e.__traceback__.tb_lineno}')
		soc.close(); soc = None
		return False, repr(e)[:200]
	soc.close(); soc = None
	return True, None

def routeros_query(
	query:list
	, device_ip:str=None
	, device_port:str='8728'
	, device_user:str='admin'
	, device_pwd:str=''
	, info:bool=False
	, connect_timeout:float=_DEF_TIMEOUT
)->tuple[bool, list[dict]]:
	''' Send query and return True, data = list of dictionaries
		or False, 'error'
		query - list with commands or list with such lists.

		Example (single query):
			routeros_query(
				query=[
					'/ip/address/print'
					, '?interface=BRIDGE'
				]
				, device_ip='router.lan'
				, device_user=u
				, device_pwd=p
			)

		Example (multiple queries):
			routeros_query(
				query=[
					['/ip/address/print'
						, '?interface=BRIDGE']
					, ['/ip/address/print'
						, '?interface=ISP1']
				]
				, device_ip='router.lan'
				, device_user=u
				, device_pwd=p
			)
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
			soc.settimeout(connect_timeout)
		except socket.error:
			soc = None
			continue
		try:
			soc.connect(sa)
		except socket.error:
			soc.close(); soc = None
			continue
		break

	if soc is None:
		if info: print('routeros_query: Could not open socket')
		return False, 'Could not open socket'

	try:
		apiros = _ApiRos(soc)
		apiros.login(device_user, device_pwd)
		results = []
		if isinstance(query[0], list):
			queries = query
		else:
			queries = [query]
		for q in queries:
			data = apiros.talk(q)

			if len(data) > 1:
				if data[0][0] == '!trap':
					if info: print(f'routeros_query: bad query')
					results.append( (False, 'bad query') )
				else:
					results.append(
						(True, [t[1] for t in data[:-1]] )
					)
			else:
				results.append( (True, []) )
		
		soc.close(); soc = None
		if isinstance(query[0], list):
			return True, results
		else:
			return results[0]
	except Exception as e:
		if info: print(f'routeros_query exception:\n{repr(e)}'
		+ f'\nat line {e.__traceback__.tb_lineno}')
		soc.close(); soc = None
		return False, repr(e)[:200]

if __name__ != '__main__': patch_import()
