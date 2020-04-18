import os
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from glob import glob

class Crypt:
	''' Get login and password from file.
		All methods returns 'status, data':
		status - boolean
		data - ['list', 'of', 'values'] in case of success or ['error
		description']
	'''
	def __init__(s, password:str, pwd_encoding:str='utf-8'
	, scrypt_args:dict=None, file_encoding:str=None):
		s.enc_file = None
		s.password = password
		s.file_encoding = file_encoding
		s.pwd_encoding = pwd_encoding
		if scrypt_args:
			s.scrypt_args = scrypt_args
		else:
			s.scrypt_args = {
				'length': 32
				, 'n': 2**19
				, 'r': 8
				, 'p': 1
				, 'backend': default_backend()
			}

	def scrypt_pwd(s, salt:str=None)->list:
		''' Returns derived password and base64 encoded salt.
			If no salt is provided then generates new salt.
		'''
		if salt: 
			salt = base64.urlsafe_b64decode(salt)
		else:
			salt = os.urandom(32)
		try:
			key = Scrypt(
				salt=salt,
				**s.scrypt_args
			).derive( bytes(s.password, s.pwd_encoding) )
			salt = base64.urlsafe_b64encode(salt).decode(s.pwd_encoding)
			return True, [key, salt]
		except Exception as e:
			return False, [repr(e)]

	def write_enc_file(s, fullpath:str, content:str):
		''' Returns filename of encrypted file (fullpath + base64(salt)
			as extension). Deletes old files with same name (without
			salt extension).
			If encoding='binary' writes content as is.
		'''
		try:
			li = glob(fullpath + '.*')
			list(map(os.remove, li))
		except Exception as e:
			return False, ['glob remove error: ' + repr(e)]
		status, data = s.scrypt_pwd()
		if not status:
			return False, ['scrypt error: ' + data[0]]
		salt = data[1]
		key = base64.urlsafe_b64encode(data[0])
		fer = Fernet(key)
		if s.file_encoding == 'binary':
			token = fer.encrypt(content)
		else:
			token = fer.encrypt(bytes(content, s.file_encoding))
		try:
			newpath = fullpath + '.' + salt
			with open(newpath, 'bw+') as f:
				f.write(token)
		except Exception as e:
			return False, ['file write error: ' + repr(e)]
		return True, [newpath]

	def read_enc_file(s, fullpath:str)->list:
		''' Returns content of encrypted file.
			fullpath - encrypted file with salt in extension.
		'''
		if not fullpath.endswith('='):
			status, data = s._find_enc_file(fullpath)
			if not status: return False, f'_find_enc_file error: {data}'
			fullpath = data
		salt = os.path.splitext(fullpath)[1][1:]
		status, data = s.scrypt_pwd(salt=salt)
		if status:
			key, salt = data
		else:
			return False, ['scrypt_pwd error: ' + data[0]]
		try:
			with open(fullpath, 'br') as f:
				token = f.read()
		except Exception as e:
			return False, ['file read error: ' + repr(e)]
		key = base64.urlsafe_b64encode(key)
		fer = Fernet(key)
		try:
			content = fer.decrypt(token)
		except Exception as e:
			return False, ['fer.decrypt error: ' + repr(e)]
		if s.file_encoding != 'binary':
			content = content.decode(encoding=s.file_encoding)
		return True, [content]
	
	def _find_enc_file(s, fullpath:str):
		''' Finds encoded file (we don't know extension because
			it's salt)
		'''
		li = glob(fullpath + '*')
		if len(li) == 1:
			return True, li[0]
		elif len(li) > 1:
			return False, ['A lot of files']
		elif len(li) == 0:
			return False, ['No such file']
		else:
			return False, ['o_O']



	

def file_enc_write(fullpath:str, content:str, password:str
, encoding:str='utf-8')->tuple:
	''' Encrypts content with password and writes to a file.
		Adds salt as file extension.
		encoding='binary' - binary mode.
		Returns fullpath.
	'''
	crypt = Crypt(password=password, file_encoding=encoding)
	status, data = crypt.write_enc_file(fullpath=fullpath, content=content)
	if not status: return False, f'write_enc_file error: {data}'
	return True, data[0]

def file_enc_read(fullpath:str, password:str
, encoding:str='utf-8')->tuple:
	''' Decrypts file and returns status, content.
		encoding='binary' - binary mode.
	'''
	crypt = Crypt(password=password, file_encoding=encoding)
	status, data = crypt.read_enc_file(fullpath=fullpath)
	if not status: return False, f'read_enc_file error: {data}'
	return True, data[0]

def file_encrypt(fullpath:str, password:str)->tuple:
	''' Encrypts file with password.
		Returns status, fullpath (or error).
		Adds salt as file extension.
	'''
	crypt = Crypt(password=password, file_encoding='binary')
	with open(fullpath, 'rb') as fi:
		status, data = crypt.write_enc_file(
			fullpath=fullpath, content=fi.read()
		)
	if not status: return False, f'write_enc_file error: {data}'
	return True, data[0]

def file_decrypt(fullpath:str, password:str)->tuple:
	''' Decrypts file with password.
		Returns status, fullpath (or error).
		Removes salt from file name.
	'''
	crypt = Crypt(password=password, file_encoding='binary')
	status, data = crypt.read_enc_file(fullpath=fullpath)
	if not status: return False, f'read_enc_file error: {data}'
	fullpath = '.'.join(fullpath.split('.')[:-1])
	with open(fullpath, 'wb+') as fi:
		fi.write(data[0])
	return True, fullpath



