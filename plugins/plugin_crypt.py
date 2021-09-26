import os
import base64
import glob
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from .tools import patch_import
_DEF_SCRYPT_ARGS = {
	'length': 32
	, 'n': 2**19
	, 'r': 8
	, 'p': 1
	, 'backend': default_backend()
}
_DEF_SALT_BYTES_SIZE = 32

class Crypt:
	''' Get login and password from file.
		All methods returns 'status, data':
		status - boolean
		data - ['list', 'of', 'values'] in case of success or ['error
		description']
	'''

	def __init__(s, password:str, pwd_encoding:str='utf-8'
	, scrypt_args:dict={}, file_encoding:str=None
	, salt_size:int=_DEF_SALT_BYTES_SIZE):
		s.enc_file = None
		s.password = password
		s.file_encoding = file_encoding
		s.pwd_encoding = pwd_encoding
		s.key = b''
		s.key_b64 = b''
		s.key_b64_str = ''
		s.salt = b''
		s.salt_b64 = b''
		s.salt_b64_str = ''
		if scrypt_args:
			s.scrypt_args = scrypt_args
		else:
			s.scrypt_args = _DEF_SCRYPT_ARGS
		s.salt_size = salt_size

	def scrypt_pwd(s, salt:str=None)->list:
		''' Returns derived password and base64 encoded salt.
			If no salt is provided then generates new salt.
		'''
		if salt: 
			salt = base64.urlsafe_b64decode(salt)
		else:
			salt = os.urandom(s.salt_size)
		try:
			s.key = Scrypt(
				salt=salt,
				**s.scrypt_args
			).derive( bytes(s.password, s.pwd_encoding) )
			s.salt = salt
			s.salt_b64 = base64.urlsafe_b64encode(salt)
			s.salt_b64_str = s.salt_b64.decode(s.pwd_encoding)
			s.key_b64 = base64.urlsafe_b64encode(s.key)
			s.key_b64_str = s.key_b64.decode(s.pwd_encoding)
			return True, None
		except Exception as e:
			return False, repr(e)

	def write_enc_file(s, fullpath:str, content:str):
		''' Returns filename of encrypted file (fullpath + base64(salt)
			as extension). Deletes old files with same name (without
			salt extension).
			If encoding='binary' writes content as is.
		'''
		try:
			li = glob.glob(fullpath + '.*')
			list(map(os.remove, li))
		except Exception as e:
			return False, f'glob remove error: {e}'
		if not s.key:
			status, data = s.scrypt_pwd()
			if not status: return False, f'scrypt error: {data}'
		fer = Fernet(s.key_b64)
		if s.file_encoding == 'binary':
			token = fer.encrypt(content)
		else:
			token = fer.encrypt(
				bytes(content, s.file_encoding) )
		try:
			newpath = fullpath + '.' + s.salt_b64_str
			with open(newpath, 'bw+') as f:
				f.write(token)
		except Exception as e:
			return False, f'file write error: {data}'
		return True, newpath

	def read_enc_file(s, fullpath:str)->list:
		''' Returns content of encrypted file.
			fullpath - encrypted file with salt in extension.
		'''
		if not fullpath.endswith('='):
			status, data = s._find_enc_file(fullpath)
			if not status: return False, f'_find_enc_file error: {data}'
			fullpath = data
		salt = os.path.splitext(fullpath)[1][1:]
		if not s.key:
			status, data = s.scrypt_pwd(salt=salt)
			if not status: return False, f'scrypt error: {data}'
		try:
			with open(fullpath, 'br') as f:
				token = f.read()
		except Exception as e:
			return False, f'file read error: {e}'
		fer = Fernet(s.key_b64)
		try:
			content = fer.decrypt(token)
		except Exception as e:
			return False, f'fernet.decrypt error: {e}'
		if s.file_encoding != 'binary':
			content = content.decode(encoding=s.file_encoding)
		return True, content
	
	def _find_enc_file(s, fullpath:str):
		''' Finds encoded file (we don't know extension because
			it's salt)
		'''
		li = glob.glob(fullpath + '*')
		if len(li) == 1:
			return True, li[0]
		elif len(li) > 1:
			return False, 'A lot of files'
		elif len(li) == 0:
			return False, 'No such file'
		else:
			return False, 'o_O'
	
	def str_enc(s, plain_text: str, encoding: str = 'utf-8'
	, salt_size:int=None) -> tuple:
		''' Encrypts string and returns
			(True, [encrypted string, salt])
			or (False, error).
			Use 'salt_size = 0' if no salt is needed.
		'''
		if not s.key:
			if salt_size != None: s.salt_size = salt_size
			status, data = s.scrypt_pwd()
			if not status: return False, f'scrypt error: {data}'
		try:
			fer = Fernet(s.key_b64)
			token = fer.encrypt(bytes(plain_text, encoding))
			return True, [token.decode(encoding), s.salt_b64_str]
		except Exception as e:
			return False, repr(e)

	def str_dec(s, enc_string: str, salt: str = ''
	, encoding: str = 'utf-8'):
		''' Decrypts string with salt and returns (True, plain_text)
		'''
		if not s.key:
			status, data = s.scrypt_pwd(salt=salt)
			if not status: return False, f'scrypt error: {data}'
		try:
			fer = Fernet(s.key_b64)
			return True, fer.decrypt(
				enc_string.encode(encoding)
			).decode(encoding)
		except Exception as e:
			return False, repr(e)

def file_enc_write(fullpath:str, content:str, password:str
, encoding:str='utf-8')->tuple:
	''' Encrypts content with password and writes to a file.
		Adds salt as file extension.
		encoding='binary' - binary mode.
		Returns fullpath.
	'''
	crypt = Crypt(password=password, file_encoding=encoding)
	status, data = crypt.write_enc_file(
		fullpath=fullpath, content=content)
	if not status: return False, f'write_enc_file error: {data}'
	return True, data

def file_enc_read(fullpath:str, password:str
, encoding:str='utf-8')->tuple:
	''' Decrypts file and returns status, content.
		encoding='binary' - binary mode.
	'''
	crypt = Crypt(password=password, file_encoding=encoding)
	status, data = crypt.read_enc_file(fullpath=fullpath)
	if not status: return False, f'read_enc_file error: {data}'
	return True, data

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
	return True, data

def file_decrypt(fullpath: str, password: str
, destination:str=None)->tuple:
	''' Decrypts file with password.
		Returns status, fullpath (or error).
		Removes salt from file name.
	'''
	crypt = Crypt(password=password, file_encoding='binary')
	status, data = crypt.read_enc_file(fullpath=fullpath)
	if not status: return False, f'read_enc_file error: {data}'
	if not destination:
		destination = '.'.join(fullpath.split('.')[:-1])
	with open(destination, 'wb+') as fi:
		fi.write(data)
	return True, destination



if __name__ == '__main__':
	print('Test (512 MB RAM required) ...')
	orig_str = 'Мы несвободны в своих поступках'
	crypt = Crypt(password='пароль',)
	d = crypt.str_enc(orig_str)[1]
	same = ( crypt.str_dec(d[0], d[1])[1] == orig_str )
	print(f'Strings are the same: {same}')
	input('Press Enter')
else:
	patch_import()