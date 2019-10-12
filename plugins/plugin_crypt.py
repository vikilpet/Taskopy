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
	, scrypt_args:dict=None):
		s.enc_file = None
		s.password = password
		s.file_encoding = None
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

	def file_encrypt(s, fullpath:str, content:str, encoding:str='utf-8'):
		''' Returns filename of encrypted file (fullpath + base64(salt)
			as extension). Deletes old files with same name (without
			salt extension).
			If encoding == 'binary' writes content as is.
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
		if encoding == 'binary':
			token = fer.encrypt(content)
		else:
			token = fer.encrypt(bytes(content, encoding))
		try:
			newpath = fullpath + '.' + salt
			with open(newpath, 'bw+') as f:
				f.write(token)
		except Exception as e:
			return False, ['file write error: ' + repr(e)]
		return True, [newpath]

	def file_decrypt(s, fullpath:str, encoding:str='utf-8')->list:
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
			content = content.decode(encoding=encoding)
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



	def get_pass_from_list(s, pw_list:list, secret:str)->list:
		''' Returns True and [login, password] from list
		'''
		if len(pw_list)==0:
			return False, ['Empty list']
		for li in pw_list:
			if len(li):
				if li[0]==secret:
					return True, li[1:3]
		return False, ['Not found: ' + secret]

	def get_secret(s, secret:str)->list:
		''' Returns [login, password] '''
		if not os.path.isfile(s.plain_file):
			status, data = s._find_enc_file()
			if not status:
				return False, ['_find_enc_file error: ' + data[0]]
			status, data = s.decrypt_file_save(data[0], s.plain_file)
			if not status:
				return False, ['decrypt_file_save error: ' + data[0]]				
		status, data  = s.get_secret_from_file(secret)
		if status:
			return True, data
		else:
			return False, ['get_secret_from_file error: ' + data[0]]

def file_enc_write(fullpath:str, content:str, password:str
, encoding:str='utf-8'):
	''' Encrypts content with password and writes to a file.
		Adds salt as file extension.
		Returns fullpath.
	'''
	crypt = Crypt(password=password)
	status, data = crypt.file_encrypt(fullpath=fullpath, content=content
									, encoding=encoding)
	if not status: return False, f'file_encrypt error: {data}'
	return True, data[0]

def file_enc_read(fullpath:str, password:str, encoding:str='utf-8'):
	''' Decrypts file and returns content.
	'''
	crypt = Crypt(password=password)
	status, data = crypt.file_decrypt(fullpath=fullpath, encoding=encoding)
	if not status: return False, f'file_decrypt error: {data}'
	return True, data[0]


