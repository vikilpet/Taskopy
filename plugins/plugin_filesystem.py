r'''
Naming convention:  
fullpath, fpath, fp - full path of a file (r'd:\soft\taskopy\crontab.py')  
fname - file name only ('crontab.py')  
relpath - relative path ('taskopy\crontab.py')  
'''


import os
import stat
import time
import glob
import csv
import random
import pyodbc
import mimetypes
import zipfile
import tempfile
import datetime
import win32con
import win32print
import hashlib
import pythoncom
import base64
import psutil
import win32file

import shutil
import configparser
import win32api
from operator import itemgetter
from zlib import crc32
from contextlib import contextmanager
from collections import namedtuple
from typing import Callable, Iterator, Iterable, Generator, Any
from win32com.shell import shell, shellcon
from pathlib import Path
from _winapi import CreateJunction
from .tools import *
from .tools import _TERMINAL_WIDTH, _SIZE_UNITS
try:
	import constants as tcon
except ModuleNotFoundError:
	import plugins.constants as tcon

_FORBIDDEN_CHARS = '<>:"\\/|?*'
_FORBIDDEN_DICT = dict(
	**{chr(d) : '%' + hex(d)[2:] for d in range(32)}
	, **{ c : '%' + hex(ord(c))[2:].upper() for c in _FORBIDDEN_CHARS}
)
_VAR_DIR = 'resources\\var'
_FILE_ATTRIBUTE_REPARSE_POINT = 1024


_MAX_PATH:int = 260

def path_long(path:str, force:bool=False):
	r'''
	Adds '\\?\' prefix to a path if it's long.
	Apply only to a string!  
	*force* - adds prefix event to a short file.  

		asrt( path_long('p'), 'p' )
		asrt( path_long('c:' + 'p'*261), '\\\\?\\c:' + 'p'*261 )
		asrt( path_long('\\\\share\\' + 'p'*261), '\\\\?\\UNC\share\\' + 'p'*261 )

	'''
	if (len(path) < _MAX_PATH) and not force: return path
	if path.startswith('\\\\?\\'): return path
	if path[1] == ':':
		return '\\\\?\\' + path
	elif path.startswith('\\\\'):
		return '\\\\?\\UNC\\' + path[2:]
	else:
		return path

def dir_slash(dirpath:str)->str:
	r'''
	Adds a trailing slash if it's not there.
	'''
	if dirpath.endswith('\\'): return dirpath
	return dirpath + '\\'

def path_get(fullpath:str|tuple|list|Iterator, max_len:int=0
, trim_suf:str='...')->str:
	r'''
	Join list of paths and optionally
	fix long path. Fill environment variables ('%APPDATA%').  
	Special variable (os.getcwd): %taskopy%  
	*max_len* - if set, then limit the
	maximum length of the full path.  

		path = path_get(('%appdata%', 'Microsoft\\Crypto'))
		asrt( dir_exists(path), True)
		path = (r'c:\Windows', '\\notepad.exe')
		path2 = r'c:\Windows\notepad.exe'
		asrt( os.path.join(*path), r'c:\notepad.exe' )
		asrt( path_get( path ), path2 )
		path = (r'c:\Windows\\', 'notepad.exe')
		asrt( path_get( path ), path2 )
		path = (r'c:\Windows\\', '\\notepad.exe')
		asrt( path_get( path ), path2 )
		asrt( path_get( path, 20 ), r'c:\Windows\no....exe' )
		asrt( path_get(r'c:\Windows\\'), 'c:\\Windows\\')
		asrt( file_exists('%taskopy%\\crontab.py'), True)

	'''
	if not fullpath: return fullpath
	if is_iter(fullpath):
		fullpath = (
			(p if n == 0 else p.lstrip('\\'))
			for n, p in enumerate(map(str, fullpath))
		)
		fullpath = (
			p[:-1] if p.endswith('\\\\') else p
			for p in map(str, fullpath)
		)
		fullpath = os.path.join(*fullpath)
	else:
		fullpath = fullpath[:-1] if fullpath.endswith('\\\\') else fullpath
	if fullpath.startswith('%'):
		env_var = fullpath[1 : ( start := fullpath.find('%', 1) )]
		rem = fullpath[start + 1: ]
		rem = rem.lstrip('\\')
		if env_var.lower() == APP_NAME.lower():
			fullpath = os.path.join( app_dir(), rem )
		else:
			fullpath = os.path.join( os.getenv(env_var), rem )
	if max_len and (len(fullpath) > max_len):
		fname, ext = os.path.splitext( os.path.basename(fullpath) )
		fdir = os.path.dirname(fullpath)
		limit = len(fullpath) - max_len + len(trim_suf)
		fullpath = os.path.join(
			fdir, fname[:-limit] + trim_suf + ext
		)
	else:
		fullpath = path_long(fullpath)
	return fullpath

def file_read(fullpath, encoding:str='utf-8', errors:str=None)->str:
	r'''
	Returns content of file

	*encoding* - if set to 'binary' then returns bytes.
	
	'''
	fullpath = path_get(fullpath)
	if encoding == 'binary':
		with open(fullpath, 'rb') as f:
			return f.read()
	else:
		with open(fullpath, 'tr', encoding=encoding, errors=errors) as f:
			return f.read()

def file_write(fullpath, content:str
, encoding:str='utf-8')->str:
	r'''
	Saves content to a file (assuming it's text, otherwise
	use `encoding='binary'`.).  
	Creates file if the fullpath doesn't exist
	and creates intermediate directories  
	If *fullpath* is '' or *None* - uses `temp_file()`.  
	Returns the fullpath.  
	'''
	if encoding == 'binary':
		open_args = {'mode': 'wb+'}
	else:
		open_args = {'mode': 'wt+', 'encoding': encoding
		, 'errors': 'ignore'}
	if fullpath:
		fullpath = path_get(fullpath)
		if not os.path.exists( d := os.path.dirname(fullpath)):
			os.makedirs(d)
	else:
		fullpath = temp_file()
	with open(fullpath, **open_args) as f:
		f.write(content)
	return fullpath

def file_ext_replace(fullpath, new_ext:str)->str:
	' Replaces file extension '
	return os.path.splitext(path_get(fullpath))[0] + '.' + new_ext

def file_rename(fullpath, dest:str
, overwrite:bool=False)->str:
	r'''
	Renames the file and returns the new name.  
	*dest* - fullpath or just new file name without parent directory.  
	*overwrite* - overwrite destination file if exists.  
	Example:

		file_rename(r'd:\\IMG_123.jpg', 'my cat.jpg')
		>'d:\\my cat.jpg'
			
	'''
	fullpath = path_get(fullpath)
	if is_iter(dest):
		dest = path_get(dest)
	elif not '\\' in dest:
		dest = os.path.join( os.path.dirname(fullpath), dest )
	dest = path_get(dest)
	try:
		os.rename(fullpath, dest)
	except FileExistsError as e:
		if overwrite:
			file_delete(dest)
			os.rename(fullpath, dest)
		else:
			raise e
	return dest

def dir_rename(fullpath, dest
, overwrite:bool=False)->str:
	r'''
	Renames path.  
	*dest* - fullpath or just new file name
	without parent directory.  
	*overwrite* - overwrite destination file
	if exists.  
	Returns destination.  
	Example:

		file_rename(r'd:\\IMG_123.jpg', 'my cat.jpg')
		>'d:\\my cat.jpg'

	'''
	fullpath = path_get(fullpath)
	dest = path_get(dest)
	if not ':' in dest:
		dest = os.path.join( os.path.dirname(fullpath), dest )
	dest = path_get(dest)
	try:
		os.rename(fullpath, dest)
	except FileExistsError as e:
		if overwrite:
			file_delete(dest)
			os.rename(fullpath, dest)
		else:
			raise e
	return dest

def file_log(fullpath, message, encoding:str='utf-8'
, time_format:str='%Y.%m.%d %H:%M:%S', sep:str='\t', end:str='\n'):
	r'''
	Logging a message.  
	'''
	fullpath = path_get(fullpath)
	with open(fullpath, 'at+', encoding=encoding) as f:
		f.write(f'{time.strftime(time_format)}{sep}{message}{end}')



def file_copy(fullpath, destination)->str:
	r'''
	Copies file to destination.  
	Destination may be a full path or directory.  
	Returns destination full path.  
	If destination file exists it will be overwritten.  
	If destination is a folder, subfolders will
	be created if they don't exist.  

		tf, td = temp_file(suffix='.txt'), temp_dir('test_fc')
		file_write(tf, 't')
		asrt(
			file_copy(tf, (td, file_name(tf) ))
			, os.path.join(td, file_name(tf) )
		)
		asrt( file_copy(tf, td), os.path.join(td, file_name(tf) ) )
		asrt(
			file_copy(tf, (td, 'nx', file_name(tf) ) )
			, os.path.join(td, 'nx', file_name(tf) )
		)
		file_delete(tf), dir_delete(td)

	'''

	fullpath = path_get(fullpath)
	destination = path_get(destination)
	if os.path.isdir(destination):
		destination = os.path.join(
			destination, os.path.basename(fullpath)
		)
	try:
		win32api.CopyFile(fullpath, destination)
	except win32api.error as e:
		if e.winerror != 3: raise
		os.makedirs( os.path.dirname(destination) )
		win32api.CopyFile(fullpath, destination)
	return destination

def file_append(fullpath, content:str, encoding:str='utf-8')->str:
	r'''
	Append content to a file. Creates *fullpath* if not specified.  
	Returns the *fullpath*.  
	'''
	if fullpath:
		fullpath = path_get(fullpath)
	else:
		fullpath = temp_file()
	with open(fullpath, 'a+', encoding=encoding) as fd:
		fd.write(content)
	return fullpath

def file_move(fullpath, destination)->str:
	r'''
	Moves the file to a new destination.  
	Returns the full path to the destination file.  
	*destination* can be a full path or just a directory.  
	If the destination path exists, it will be overwritten.  
	'''
	fullpath = path_get(fullpath)
	destination = path_get(destination)
	if os.path.isdir(destination):
		new_fullpath = dir_slash(destination) \
			+ os.path.basename(fullpath)
	else:
		new_fullpath = destination
	assert new_fullpath != fullpath \
	, "You can't move the file itself into itself"
	try:
		file_delete(new_fullpath)
	except FileNotFoundError:
		pass
	shutil.move(fullpath, new_fullpath)
	return new_fullpath



def file_delete(fullpath)->int:
	r'''
	Deletes the file permanently.  
	Returns *0* on success or if the file does not exist.  

		bmark(
			lambda fls: tuple(file_delete(f) for f in fls)
			, ( tuple(temp_file(content='t') for _ in range(3)), )
			, b_iter=1
		)
		asrt( file_delete( temp_file(content='t') ), 0 )

	'''
	fullpath = path_get(fullpath)
	last_err:int = 0
	while True:
		try:
			win32api.DeleteFile(fullpath)
			return 0
		except Exception as e:
			last_err = e.args[0]
			if last_err == 2:
				return 0
			elif last_err == 5:
				try:
					win32api.SetFileAttributes(fullpath
					, win32con.FILE_ATTRIBUTE_NORMAL)
				except:
					break
			elif last_err == 32:
				break
			else:
				break
	return last_err

def file_recycle(fullpath, silent:bool=True)->bool:
	r'''
	Move file to the recycle bin.  
	*silent* - do not show standard windows
	dialog to confirm deletion.  
	Returns `True` on successful operation.  

	NOTES: with `silent=True` large files that cannot be placed in the
	recycle garbage can will be permanently deleted without notification.  

	'''
	fullpath = path_get(fullpath)
	flags = shellcon.FOF_ALLOWUNDO
	if silent:
		flags = flags | shellcon.FOF_SILENT | shellcon.FOF_NOCONFIRMATION
	result = shell.SHFileOperation((
		0
		, shellcon.FO_DELETE
		, fullpath
		, None
		, flags
		, None
		, None
	))
	return result[0] <= 3

def dir_copy(fullpath, destination:str
, symlinks:bool=False)->int:
	''' Copy a folder with all content to a new location.
		Returns number of errors.
	r'''
	fullpath = path_get(fullpath)
	destination = path_get(destination)
	err = 0
	try:
		shutil.copytree(fullpath, destination, symlinks=symlinks)
	except FileExistsError:
		pass
	except Exception as e:
		err += 1
		qprint(f'dir_copy exception: {repr(e)}')
	return err

def _dir_create(directory:str):
	r'''
	Safely create a director even if the directory already exists.
	'''
	try:
		win32file.CreateDirectory(directory, None)
	except win32file.error as err:
		if err.winerror != 183: raise

def dir_create(fullpath=None)->str:
	r'''
	Creates new dir and returns full path.  
	If `fullpath=None` then creates temporary directory.  
	'''
	fullpath = path_get(fullpath)
	if not fullpath: return temp_dir('rnd')
	fullpath = fullpath.rstrip('.').rstrip(' ')
	os.makedirs(fullpath, exist_ok=True)
	return fullpath



def dir_delete(fullpath)->dict[str, str]:
	r'''
	Deletes folder with it's contents.  
	Returns an error dictionary of the form {'file': 'error text'}.  
	Does not raise an exception when an error occurs.  

		asrt( dir_delete( dir_test() ), {} )

	'''
	fullpath = path_get(fullpath)
	subdirs, errors = [], {}
	for dirpath, dirnames, filenames in os.walk(
		path_long(fullpath, force=True)
	):
		for sdir in dirnames: subdirs.append(dir_slash(dirpath) + sdir)
		for fname in filenames:
			fpath = dir_slash(dirpath) + fname
			if (err := file_delete(fpath)) != 0:
				errors[fpath[4:]] = f'file del {err}'
	if not errors:
		subdirs.append(path_long(fullpath, force=True))
	subdirs.sort(reverse=True)
	for sdir in subdirs:
		try:
			win32file.RemoveDirectory(sdir)
		except Exception as e:
			errors[sdir[4:]] = e.args[2].rstrip('.')
	return errors

def dir_exists(fullpath)->bool:
	return os.path.isdir( path_get(fullpath) )

def file_exists(fullpath)->bool:
	r'''
	Is file exists? It works the same way for directories.

		asrt( file_exists(r'c:\Windows'), True )
		asrt( bmark(file_exists, (random_str(),), b_iter=3), 40_000 )
		asrt( bmark(file_exists, (r'c:\Windows\notepad.exe',), b_iter=3), 60_000 )
	
	'''
	fullpath = path_get(fullpath)
	try:
		win32file.GetFileAttributesEx(fullpath)
	except:
		return False
	return True


def path_exists(fullpath)->bool:
	r''' Check if directory or file exist '''
	fullpath = path_get(fullpath)
	p = Path(fullpath)
	return p.exists()

def file_size(fullpath, unit:str='b')->int:
	r'''
	Gets the file size in the specified units.  

		fpath = r'c:\Windows\System32\notepad.exe' # on SSD
		bmark(win32file.GetFileAttributesEx, fpath)
		bmark(os.stat, fpath)

	'''
	fullpath = path_get(fullpath)
	e = _SIZE_UNITS.get(unit.lower(), 1)
	return win32file.GetFileAttributesEx(fullpath)[4] // e

def file_size_str(fullpath)->str:
	r'''
	Size of file *for humans*.  
	Example:

		file_size_str(r'c:\\my_file.bin')
		>'5 MB'
		file_size_str(336013)
		>'328.1 KB'

	'''
	if isinstance(fullpath, (int, float)):
		size = fullpath
	else:
		fullpath = path_get(fullpath)
		size = os.stat(fullpath).st_size
	for unit in list(_SIZE_UNITS.keys())[::-1]:
		if abs(size) < 1024.0:
			return f'{size:.1f} {unit.upper()}'
		size /= 1024.0

def file_ext(fullpath)->str:
	r'''
	Returns file extension in lower case without dot.

		asrt(file_ext('crontab.py'), 'py')
		asrt(file_ext('crontab.'), '')
		asrt(file_ext('crontab.py.py'), 'py')
		asrt(file_ext('crontab.py.'), '')

	'''
	fullpath = path_get(fullpath)
	ext = os.path.splitext(fullpath)[1].lower()
	if ext == '': return ext
	return ext[1:]

def file_basename(fullpath)->str:
	r'''
	Returns basename: file name without 
	parent folder and extension. Example:

		asrt( file_basename(r'c:\pagefile.sys'), 'pagefile')

	'''
	fullpath = path_get(fullpath)
	fname = os.path.basename(fullpath)
	return os.path.splitext(fname)[0]

def file_name_add(fullpath, suffix:str='', prefix:str='')->str:
	r'''
	Adds suffix or prefix to a file name.  
	Example:  

		asrt( file_name_add('my_file.txt', suffix='_1'), 'my_file_1.txt' )
		asrt( file_name_add('my_file.txt', prefix='~'), '~my_file.txt' )

	'''
	fullpath = path_get(fullpath)
	if not isinstance(suffix, str): suffix = str(suffix)
	if not isinstance(prefix, str): prefix = str(prefix)
	par_dir, name = os.path.split(fullpath)
	basename, ext = os.path.splitext(name)
	return os.path.join(par_dir, prefix + basename + suffix + ext)

def file_name_rem(fullpath, suffix:str='', prefix:str='')->str:
	r'''
	Removes a suffix or prefix from a filename.  
	Example:

		asrt( file_name_rem('my_file_1.txt', suffix='_1'), 'my_file.txt')
		asrt( file_name_rem('my_file_1.txt', suffix='_'), 'my_file_1.txt')
		asrt( file_name_rem('tmp_foo.txt', prefix='tmp_'), 'foo.txt')
	
	'''
	fullpath = path_get(fullpath)
	if suffix: suffix = str(suffix)
	if prefix: prefix = str(prefix)
	par_dir, name = os.path.split(fullpath)
	basename, ext = os.path.splitext(name)
	if prefix and basename.startswith(prefix):
		basename = basename[ len(prefix) : ]
	if suffix and basename.endswith(suffix):
		basename = basename[ : - len(suffix) ]
	return os.path.join(par_dir, basename + ext)

def file_name_fix(filename:str, repl_char:str='_')->str:
	r'''
	Replaces forbidden characters with the *repl_char*.  
	Don't use it with a full path or it will replace
	all backslashes.  
	Removes the leading and trailing spaces and dots.  
	'''
	new_fn = ''
	for char in filename.strip(' .'):
		if (char in _FORBIDDEN_CHARS
		or ord(char) < 32):
			new_fn += repl_char
		else:
			new_fn += char
	return new_fn

def dir_dirs(fullpath, subdirs:bool=True, parent:bool=False)->Iterator[str]:
	r'''
	Returns list of full paths of all directories
	in this directory and its subdirectories.  
	*fullpath* (source directory) is not included in results.  
	*parent* - include *fullpath* too.  

		asrt( r'c:\windows\System32' in dir_dirs(r'c:\windows', False), True )
		asrt( r'c:\windows' in dir_dirs(r'c:\windows', False), False )
		asrt( r'c:\windows' in dir_dirs(r'c:\windows', subdirs=False, parent=True), True )

	'''
	fullpath = path_get(fullpath)
	if parent: yield fullpath
	for dirpath, dirs, _ in os.walk(path_long(fullpath, force=True)
	, topdown=True):
		for d in dirs: yield dir_slash(dirpath[4:]) + d
		if not subdirs: return

def dir_files(fullpath, subdirs:bool=True, name_only:bool=False
, **rules)->Iterator[str]:
	r'''
	Returns list of full filenames of all files
	in the given directory and its subdirectories.  
	*subdirs* - including files from subfolders.  
	*rules* - rules for the `path_rule` function  
	*name_only* - returns filenames, not the full path.  

		pdir = path_get((app_dir(), 'plugins'))
		asrt(
			tuple(dir_files( pdir, in_ext='jpg') )
			, tuple()
		)
		asrt(
			tuple(dir_files( pdir, name_only=True, in_ext='py') )[0]
			, 'constants.py'
		)
		asrt(
			tuple( dir_files(pdir, ex_ext='pyc') )
			, tuple( dir_files(pdir, in_ext='py') )
		)
		asrt(
			tuple( dir_files(pdir, ex_path='plugins\\') )
			, tuple()
		)
		asrt(
			tuple( dir_files(pdir, name_only=True, in_name='tools.py') )
			, ('tools.py',)
		)
		td = dir_test(sdirnum=3)
		asrt( len( tuple( dir_files(td) ) ), 3 )
		dir_delete(td)

	'''

	fullpath = path_get(fullpath)
	if rules: in_rules, ex_rules = path_rule(**rules)
	for dirpath, dirs, filenames in os.walk(path_long(fullpath, force=True)
	, topdown=True):
		if not subdirs: dirs.clear()
		for fname in filenames:
			if rules:
				fpath = dir_slash(dirpath) + fname
				if _path_match(
					path=fpath
					, in_rules=in_rules
					, ex_rules=ex_rules
				):
					yield fname if name_only else fpath[4:]
			else:
				 yield fname if name_only else dir_slash(dirpath[4:]) + fname

def dir_rnd_files(fullpath, file_num:int=1
, attempts:int=5, **rules)->Iterator[str]:
	r'''
	Gets random files from a directory or `None`
	if nothing is found.  
	*file_num* - how many files to return.  
	*rules* - a tuple of rules from the `path_rule`.

	Designed for large directories that take a significant
	amount of time to list.  
	The function will not return the same file twice.  
	Example:

		dir_rnd_files('.')
		tuple(dir_rnd_files('.', ex_ext='py'))
	
	Compared to `dir_files` with `random.choice`:

		> bmark(lambda: random.choice( list(dir_files(temp_dir() ) ) ), b_iter=10)
		bmark: 113 367 113 ns/loop

		> bmark(dir_rnd_files, a=(temp_dir(), ), b_iter=10)
		620

		> len( tuple( dir_files( temp_dir() ) ) )
		1914
		
	'''
	fullpath = path_get(fullpath)
	uniq = set()
	in_rules, ex_rules = path_rule(**rules)
	for _ in range(file_num):
		for _ in range(attempts):
			path = fullpath
			if len(uniq) == file_num: return
			for _ in range(attempts):
				try:
					dlist = os.listdir(path)
				except PermissionError:
					break
				if not dlist: break
				path = os.path.join(path, random.choice(dlist) )
				if os.path.isfile(path):
					if (
						(not rules)
						or _path_match(
							path
							, in_rules=in_rules
							, ex_rules=ex_rules
						)
					) and (not path in uniq):
						uniq.add(path)
						yield path
						break
					else:
						break

def dir_rnd_dirs(fullpath, attempts:int=5
, filter_func=None)->str:
	r'''
	Same as `dir_rnd_file`, but returns the subdirectories.
	'''
	fullpath = path_get(fullpath)
	for _ in range(attempts):
		path = fullpath
		for _ in range(attempts):
			dlist = os.listdir(path)
			if not dlist: break
			path = os.path.join(path, random.choice(dlist) )
			if os.path.isdir(path):
				if not filter_func: return path
				if filter_func(path):
					return path
				else:
					break
			else:
				break
	return None

def dir_purge(fullpath, days:int=0, subdirs:bool=True
, creation:bool=False, test:bool=False
, print_del:bool=False, **rules)->int:
	r'''
	Deletes files older than *x* days.  
	Deletes empty subfolders.  
	Returns number of deleted files and folders.  
	
	*days=0* - delete everything  
	*creation* - use date of creation, otherwise use last
	modification date.  
	*subdirs* - delete in subfolders too. Empty subfolders 
	will be deleted.  
	*test* - only display the files and folders that should be deleted, without actually deleting them.  
	*print_del* - print path when deleting.  
	*rules* - rules for the `path_rule` function  

		td = dir_test(sdirnum=2)
		asrt( len( tuple( dir_files(td) ) ), 2 )
		dir_purge(td, days=0, subdirs=True)
		asrt(
			len( tuple( dir_files(td) ) )
			, 0
		)
		dir_delete(td)

	'''
	def print_d(fn:str, reason:str):
		if print_del:
			qprint('dir_purge:', reason, os.path.relpath(fn, fullpath))

	def robust_remove_file(fn):
		nonlocal counter
		print_d(fn, 'file')
		if file_delete(fn) == 0: counter += 1
		
	def robust_remove_dir(fn):
		nonlocal counter
		try:
			print_d(fn, 'dir')
			dir_delete(fn)
			counter += 1
		except:
			pass
		
	def fn_print(fn):
		nonlocal counter
		counter += 1
		qprint(os.path.relpath(fn, fullpath))

	fullpath = path_get(fullpath)
	counter = 0
	dirs = ()
	files = ()
	if subdirs:
		files = dir_files(fullpath, subdirs=True)
		dirs = dir_dirs(fullpath, subdirs=True)
	else:
		files = dir_files(fullpath, subdirs=False)
	if days < 0: days = -days
	drule = 'in_datec_bef' if creation else 'in_datem_bef'
	rules[drule] = datetime.timedelta(days=days)
	files = path_filter(files, **rules)
	if test:
		file_func = fn_print
		dir_func = fn_print
	else:
		file_func = robust_remove_file
		dir_func = robust_remove_dir
	for fpath in files: file_func(fpath)
	for fpath in dirs:
		if not any(
			len(t[2]) for t in os.walk( path_long(fpath, force=True ) )
		):
			dir_func(fpath)
	return counter

def file_name(fullpath)->str:
	r'''
	Returns only the filename from the fullpath.  
	
		asrt( file_name(r'C:\Windows\System32\calc.exe'), 'calc.exe' )
		# Note: for a directory with a slash at the end
		asrt( file_name('C:\\Windows\\System32\\'), '' )
		asrt( file_name('C:\\Windows\\System32'), 'System32' )

	'''
	return os.path.basename( path_get(fullpath) )

def file_name_wo_ext(fullpath)->str:
	return os.path.splitext(path_get(fullpath))[0]

def file_dir(fullpath)->str:
	r'''
	Returns directory from fullpath.  
	
		asrt( bmark(file_dir, r'c:\Windows\System32\calc.exe'), 5617 )
		asrt( file_dir(r'sdcard/Music/file.mp3'), r'sdcard/Music')
	
	'''
	return os.path.dirname(path_get(fullpath))

def file_dir_repl(fullpath, new_dir:str)->str:
	r'''
	Changes the directory of the file (in full path)
	'''
	fullpath = path_get(fullpath)
	return os.path.join(new_dir, os.path.basename(fullpath) )

def file_backup(fullpath, dest_dir:str=''
, suffix_format:str='_%y-%m-%d_%H-%M-%S')->str:
	r'''
	Copy *somefile.txt* to *backup_dir\somefile_2019-05-19_21-23-02.txt*  
	Returns full path of the new file.  
	Does not change the date of the file.  

	*dest_dir* - destination directory.
	If not specified - current folder.  
	'''
	fullpath = path_get(fullpath)
	if not dest_dir: dest_dir = os.path.dirname(fullpath)
	if not os.path.isdir(dest_dir): dir_create(dest_dir)
	name, ext = os.path.splitext(
		os.path.basename(fullpath)
	)
	destination = os.path.join(
		dest_dir
		, name	+ time.strftime(suffix_format) + ext
	)
	shutil.copy2(fullpath, destination)
	return destination

def file_update(src_file, dst_file)->bool:
	r'''
	Overwrites the file *dst_file* with the file *src_file*
	if the latter is newer or *dst_file* does not exists.  
	Returns `True` if update occured.  
	'''
	src_file = path_get(src_file)
	dst_file = path_get(dst_file)
	is_copy_needed:bool = False
	is_md_needed:bool = False
	try:
		win32file.GetFileAttributesEx(dst_file)
	except:
		is_copy_needed = True
		is_md_needed = True
	else:
		is_copy_needed = win32file.GetFileAttributesEx(src_file)[3] \
		> win32file.GetFileAttributesEx(dst_file)[3]
	if not is_copy_needed: return False
	if is_md_needed: _dir_create(os.path.dirname(dst_file))
	win32file.CopyFile(src_file, dst_file, False)
	return True

def drive_free(path:str, unit:str='GB')->int:
	r'''
	Returns drive free space in specified unit.  
	You can just specify the full path here
	, so you don't need to extract the drive letter.  

		asrt( drive_free('c'), 0, '>')
		asrt( drive_free('c:\\windows'), 10, '>')
		asrt( drive_free('c:\\windows\\'), 10, '>')
		asrt( bmark(drive_free, 'c'), 35_000 )

	'''
	e = _SIZE_UNITS.get(unit.lower(), 1073741824)
	if len(path) == 1:
		path = f'{path}:\\'
	try:
		return win32api.GetDiskFreeSpaceEx(path)[2] // e
	except:
		return -1

def dir_list(fullpath, subdirs:bool=True, **rules)->Iterator[str]:
	r'''
	Returns all directory content (dirs and files).  
	*rules* - rules for the `path_rule` function.  

		rdir = path_get( (app_dir(), 'resources') )
		asrt( 'icon.png' in (file_name(f) for f in dir_list(rdir) ), True)
		asrt(
			'icon.png' in (file_name(f) for f
				in dir_list('resources', ex_ext='png'))
			, False
		)
		asrt(
			bmark(lambda d: tuple(dir_list(d)), 'log', b_iter=5)
			, 100_000
		)

	'''
	fullpath = path_get(fullpath)
	if rules: in_rules, ex_rules = path_rule(**rules)
	for dirpath, dirnames, filenames in os.walk(
		path_long(fullpath, force=True)
	):
		for d in dirnames:
			fpath = dir_slash(dirpath) + d
			if rules:
				if _path_match(
					path=fpath
					, in_rules=in_rules
					, ex_rules=ex_rules
				):
					yield fpath[4:]
			else:
				yield fpath[4:]
		for fn in filenames:
			fpath = dir_slash(dirpath) + fn
			if rules:
				if _path_match(
					path=fpath
					, in_rules=in_rules
					, ex_rules=ex_rules
				):
					yield fpath[4:]
			else:
				yield fpath[4:]
		if not subdirs: return

def dir_find(fullpath, only_files:bool=False)->list:
	'''
	Returns list of paths in specified folder.  
	*fullpath* passed to **glob.glob**  
	*only_files* - return only files and not
	files and directories  

	Examples:
		dir_find('d:\\folder\\*.jpg')
		dir_find('d:\\folder\\**\\*.jpg')

	'''
	
	fullpath = path_get(fullpath)
	if not '*' in fullpath: fullpath = os.path.join(fullpath, '*')
	subdirs = ('**' in fullpath)
	fullpath = fullpath.replace('[', '[[]')
	paths = glob.glob(fullpath, recursive=subdirs)
	if fullpath.endswith('\\**'):
		try:
			paths.remove(fullpath.replace('**', ''))
		except ValueError:
			pass
	if not only_files: return paths
	files = []
	for path in paths:
		if os.path.isfile(path):
			files.append(path)
	return files

def csv_read(fullpath, encoding:str='utf-8', fieldnames:tuple=None
, delimiter:str=';', quotechar:str='"')->list:
	''' Read whole CSV file and return content as list of dictionaries.
		If no fieldnames is provided uses first row as fieldnames.
		All cell values is strings.
	'''
	fullpath = path_get(fullpath)
	with open(fullpath, 'r', encoding=encoding) as f:
		reader = csv.DictReader(f, skipinitialspace=True, fieldnames=fieldnames
		, delimiter=delimiter, quotechar=quotechar)
		li = [dict(row) for row in reader]
	return li

def csv_write(fullpath, content:list, fieldnames:tuple=None
, encoding:str='utf-8', delimiter:str=';', quotechar:str='"'
, quoting:int=csv.QUOTE_MINIMAL)->str:
	''' Writes list of dictionaries as CSV file.
		If fieldnames is None then takes keys() from
		first list item as field names.
		Returns the fullpath.
		content example:
		[
			{'name': 'some name',
			'number': 1}
			, {'name': 'another name',
			'number': 2}
			...	
		]
	'''
	fullpath = path_get(fullpath)
	if not fieldnames:
		fieldnames = content[0].keys()
	with open(fullpath, 'w', encoding=encoding
	, errors='ignore', newline='') as f:
		writer = csv.DictWriter(
			f
			, fieldnames=fieldnames
			, delimiter=delimiter
			, quotechar=quotechar
			, quoting=quoting
		)
		writer.writeheader()
		writer.writerows([di for di in content])
	return fullpath

def dir_size(fullpath, unit:str='b', skip_err:bool=True)->int:
	r'''
	Returns directory size (without symlinks).  
	*skip_err* - do not raise an exeption on unavailable files.  

		asrt( bmark(dir_size, a=('logs',), b_iter=1 ) , 150_000 )

	'''
	fullpath = path_get(fullpath)
	udiv = _SIZE_UNITS.get(unit.lower(), 1)
	total_size = 0
	for dirpath, _, filenames in os.walk(path_long(fullpath, force=True)):
		for fname in filenames:
			fpath = dir_slash(dirpath) + fname
			try:
				atts = win32file.GetFileAttributesEx(fpath)
			except Exception as e:
				if skip_err:
					tdebug(f'skip {path_short(fpath[4:], 50)}'
					, f' ({e.args[2]})', short=True)
					continue
				else:
					raise e
			if (
				atts[0] & _FILE_ATTRIBUTE_REPARSE_POINT
					== _FILE_ATTRIBUTE_REPARSE_POINT
			):
				tdebug(f'skip link: {fname}')
				continue
			total_size += atts[4]
	return total_size // udiv

def dir_zip(fullpath, destination=None
, do_cwd:bool=False)->str:
	r'''
	Compresses folder and returns the full path to archive.  
	If destination is a folder then take
	archive name from fullpath directory name.
	Overwrites the destination if it exists.
	If destination is not specified then create
	archive in same directory.  
	Returns destination.  
	'''
	EXT = 'zip'
	fullpath = path_get(fullpath)
	fullpath = fullpath.strip('\\')
	destination = path_get(destination)
	if not destination:
		new_fullpath = os.path.join(
			os.path.dirname(fullpath)
			, os.path.basename(fullpath)
		)
		base_name = os.path.basename(fullpath)
		new_fullpath += '.zip'
	elif os.path.isdir(destination):
		new_fullpath = dir_slash(destination) \
			+ os.path.basename(fullpath)
		base_name = os.path.basename(fullpath)
		new_fullpath += '.zip'
	else:
		new_fullpath = destination
		if not new_fullpath.endswith('.zip'):
			new_fullpath += '.zip'
		base_name = os.path.basename(new_fullpath)
		if base_name.lower().endswith('.zip'):
			base_name = base_name[:-4]
	root_dir = os.path.dirname(fullpath)
	base_dir = os.path.basename(
		fullpath.strip(os.sep))
	if do_cwd:
		with working_directory(os.path.dirname(new_fullpath)):
			result = shutil.make_archive(base_name, format=EXT
				, root_dir=root_dir, base_dir=base_dir)
	else:
		result = shutil.make_archive(base_name, format=EXT
			, root_dir=root_dir, base_dir=base_dir)
		try:
			os.makedirs(os.path.dirname(new_fullpath))
		except FileExistsError:
			pass
		shutil.move(result, new_fullpath)
	return new_fullpath

def file_unzip(fullpath, dst_dir:str)->str:
	r'''
	Extracts the contents of a zip file to the destination directory.  
	Returns *fullpath*.  
	Raises:  
		zipfile.BadZipFile: If the file is not a valid zip file.  
		PermissionError: If there's no permission to read/write.  
	'''
	fullpath = path_get(fullpath)
	os.makedirs(dst_dir, exist_ok=True)
	with zipfile.ZipFile(fullpath, 'r') as zip_ref:
		for member in zip_ref.infolist():
			target_path = os.path.join(dst_dir, member.filename)
			if not target_path.startswith(os.path.normpath(dst_dir) + os.sep):
				raise ValueError(f"Security risk: attempted path traversal in zip file: {member.filename}")
		zip_ref.extractall(dst_dir)
	return fullpath

def file_zip(fullpath, destination=None)->str:
	r'''
	Compresses a file or files to archive.  
	*fullpath* - string with full path or list with fullpaths.  
	*destination* - full path to the archive or destination directory.  
	'''
	fullpath = path_get(fullpath)
	destination = path_get(destination)
	if not destination:
		destination = file_ext_replace(fullpath, 'zip')
	if isinstance(fullpath, str):
		if file_ext(destination) != 'zip':
			dir_create(destination)
			destination = os.path.join(
				destination
				, file_ext_replace(os.path.basename(fullpath), 'zip')
			)
		with zipfile.ZipFile(
			destination, 'w'
		) as zipf:
			zipf.write(fullpath, arcname=os.path.basename(fullpath)
				, compress_type=zipfile.ZIP_DEFLATED)
		return destination
	elif isinstance(fullpath, (list, tuple)):
		with zipfile.ZipFile(
			destination, 'w'
		) as zipf:
			for fi in fullpath:
				zipf.write(fi, arcname=os.path.basename(fi)
					, compress_type=zipfile.ZIP_DEFLATED)
		return destination
	else:
		return Exception('file_zip: unknown type of fullpath')

def file_zip_cont(fullpath, only_files:bool=False)->list:
	' Returns list of paths in zip file'
	fullpath = path_get(fullpath)
	with zipfile.ZipFile(fullpath) as z:
		if only_files:
			return [f.filename for f in z.filelist
				if getattr(f, 'compress_type', None)]
		else:
			return [f.filename for f in z.filelist]


def temp_dir(new_dir:str='', prefix:str='', suffix:str='')->str:
	r'''
	Returns the full path to the user's temporary directory.  
	No trailing slash.  
	If *new_dir* is specified, creates this subfolder and
	returns the path to it.  
	*prefix*, *suffix* - add something to a directory name.  
	If *new_dir='rnd'* then a directory with a random name is created.  

		# No subdirectory is created:
		asrt( temp_dir(), os.getenv('temp') )
		asrt( bmark(temp_dir), 1_700 )
		# A subdirectory is created with the prefix:
		# temp_dir(prefix='test_')
		# > 'c:\\temp\\user\\test_0108180259UyEy'

	'''
	dst_dir = win32api.GetTempPath().rstrip('\\')
	if all((new_dir == '', prefix == '', suffix == '')): return dst_dir
	new_dir, prefix, suffix = str(new_dir), str(prefix), str(suffix)
	dname:str = str(new_dir)
	if (dname == 'rnd') or ((dname == '') and (suffix != '' or prefix != '')):
		dname = time.strftime("%m%d%H%M%S") + random_str(4)
	if prefix or suffix:
		dname = file_name_add(dname, suffix=suffix, prefix=prefix)
	dst_dir = os.path.join(dst_dir, dname)
	try:
		os.mkdir(dst_dir)
	except FileExistsError:
		pass
	return dst_dir

def temp_file(prefix:str='', suffix:str=''
, content=None, encoding='utf-8', time_format:str='%m%d%H%M%S'
, rnd_len:int=4)->str:
	r'''
	Returns the full name for the temporary file.
	(the file is not created as such)  
	If *content* is specified then writes content to the file.  
	'''
	fname = os.path.join(
		tempfile.gettempdir()
		, prefix + time.strftime(time_format)
		+ random_str(rnd_len) + suffix
	)
	if content: file_write(fname, content=content, encoding=encoding)
	return fname

def file_hash(fullpath, algorithm:str='crc32'
, buf_size:int=2**18)->str:
	r'''
	Returns hash of file.  
	*algorithm* -- 'crc32' or any algorithm
	from hashlib ('md5', 'sha512' etc).  
	'''
	fullpath = path_get(fullpath)
	algorithm = algorithm.lower().replace('-', '')
	if algorithm == 'crc32':
		prev = 0
		for eachLine in open(fullpath, 'rb'):
			prev = crc32(eachLine, prev)
		return '%X' % (prev & 0xFFFFFFFF)
	else:
		with open(fullpath, 'rb') as fi:
			return hashlib.file_digest(
				fi, algorithm, _bufsize=buf_size
			).hexdigest()
	
def drive_list(exclude:str='')->str:
	r'''
	Returns a string of local drive letters in lower case.  
	*exclude* - drives to exclude.  
	'''
	drives = win32api.GetLogicalDriveStrings() \
		.replace(':\\\000', '').lower()
	for ch in exclude:
		drives = drives.replace(ch, '')
	return drives

@contextmanager
def working_directory(directory:str):
	'''
	Change current working directory
	and revert it back. You would better never use this.
	'''
	owd = os.getcwd()
	try:
		os.chdir(directory)
		yield directory
	finally:
		os.chdir(owd)


def file_date_m(fullpath)->datetime.datetime:
	'''
	Returns file modification date in datetime.  
	Drop microseconds:

		file_date_m(r'...').replace(microsecond=0)

	'''
	fullpath = path_get(fullpath)
	ts = os.path.getmtime(fullpath)
	return datetime.datetime.fromtimestamp(ts)

def file_date_c(fullpath)->datetime.datetime:
	' Returns file creation date in datetime '
	fullpath = path_get(fullpath)
	ts = os.path.getctime(fullpath)
	return datetime.datetime.fromtimestamp(ts)

def file_date_a(fullpath)->datetime.datetime:
	' Returns file access date in datetime '
	fullpath = path_get(fullpath)
	ts = os.path.getatime(fullpath)
	return datetime.datetime.fromtimestamp(ts)

def file_attr_set(fullpath
, attribute:int=win32con.FILE_ATTRIBUTE_NORMAL):
	'''
	Sets file attribute.  
	Type 'win32con.FILE_' to get syntax hints for
	constants.
	'''
	win32api.SetFileAttributes(path_get(fullpath), attribute)

def file_date_get(fullpath)->tuple[dtime, dtime, dtime]:
	r'''
	Returns tuple(creation time, access time, modification time)

		fpath = temp_file(content=' ')
		asrt( file_date_get(fpath)[2].minute, time_minute() )
		asrt( bmark(file_date_get, (fpath,)), 80_000 )
		file_delete(fpath)

	'''
	pywindate = win32file.GetFileAttributesEx(path_get(fullpath))[1:4]
	return tuple(
		datetime.datetime(d.year, d.month, d.day, d.hour, d.minute
		, d.second, d.microsecond)
		for d in (d.astimezone() for d in pywindate)
	)

def file_date_set(fullpath, datec=None, datea=None, datem=None):
	r'''
	Sets a file date.  

		fp = temp_file(content=' ')
		asrt(
			bmark(file_date_set
				, ka={'fullpath': fp, 'datec': time_now()}, b_iter=3)
			, 220_000
		)
		file_delete(fp)

	'''
	handle = win32file.CreateFile(
		path_get(fullpath)
		, win32file.GENERIC_WRITE
		, 0
		, None
		, win32file.OPEN_EXISTING
		, 0
		, 0
	)
	for d in (datec, datea, datem):
		if d: d = d.timestamp()
	win32file.SetFileTime(
		handle, datec, datea, datem
	)
	handle.close()


def shortcut_create(fullpath, dest:str|tuple, descr:str=''
, icon_fullpath:str|tuple='', icon_index:int=-1
, win_style:int=win32con.SW_SHOWNORMAL, cwd:str=''
, hotkey:int=0)->str:
	r'''
	Creates shortcut to the file.  
	Returns full path of shortcut.  

	*dest* - shortcut destination. If `None` then
	use desktop path of current user.  
	*descr* - shortcut description. 
	*icon_fullpath* - source file for icon.  
	*icon_index* - if specified and icon_fullpath is `None`
	then fullpath is used as icon_fullpath.  
	'''
	fullpath = path_get(fullpath)
	dest = path_get(dest)
	icon_fullpath = path_get(icon_fullpath)
	if not descr: descr = file_name(fullpath)
	if not dest:
		dest = os.path.join(
			dir_user_desktop()
			, file_name(fullpath)
		)
	elif dir_exists(dest):
		dest = os.path.join(dest, file_name(fullpath) )
	if not dest.endswith('lnk'): dest = file_ext_replace(dest, 'lnk')
	if icon_index != -1 and not icon_fullpath:
		icon_fullpath = fullpath
	if icon_fullpath and icon_index == -1: icon_index = 0
	pythoncom.CoInitialize()
	shortcut = pythoncom.CoCreateInstance (
		shell.CLSID_ShellLink
		, None
		, pythoncom.CLSCTX_INPROC_SERVER
		, shell.IID_IShellLink
	)
	shortcut.SetPath( os.path.abspath(fullpath) )
	shortcut.SetDescription(descr)
	shortcut.SetShowCmd(win_style)
	if hotkey: shortcut.SetHotKey(hotkey)
	if cwd: shortcut.SetWorkingDirectory(cwd)
	if icon_index != -1: shortcut.SetIconLocation(icon_fullpath, icon_index)
	persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
	persist_file.Save(dest, 0)
	pythoncom.CoUninitialize()
	return dest

def file_print(fullpath, printer:str=None
, use_alternative:bool=False)->bool:
	r'''
	Prints file on specified printer. Non-blocking.  
	Returns True on success.  
	If no printer is specified, printing is performed
	on the default system printer.  
	'''
	fullpath = path_get(fullpath)
	if ' ' in fullpath: fullpath = f'"{fullpath}"'
	if not printer:
		try:
			printer = win32print.GetDefaultPrinter()
		except RuntimeError:
			return False
	verb = 'print'
	printer_str = f'"/d:{printer}"'
	if use_alternative:
		verb = 'printto'
		printer_str = f'"{printer}"'
	win32api.ShellExecute (
		0
		, verb
		, fullpath
		, printer_str
		, '.'
		, 0
	)
	return True

def dir_user_desktop()->str:
	' Returns full path to the desktop directory of current user '
	return shell.SHGetFolderPath(
		0, shellcon.CSIDL_DESKTOP, 0, 0)

def dir_user_startup()->str:
	' Returns full path to the startup directory of current user '
	return shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0)

def file_b64_enc(fullpath:str)->str:
	'''
	Encodes a file to the base64 string.
	'''
	fullpath = path_get(fullpath)
	with open(fullpath, 'rb') as fd:
		return base64.b64encode(fd.read()).decode('utf-8')

def file_b64_dec(b64_str:str)->bytes:
	'''
	Decodes a file (to bytes) from the base64 string.
	'''
	return base64.b64decode(b64_str)

class HTTPFile:

	HTTPFile = True
	
	def __init__(
		self
		, fullpath
		, use_save_to:bool=False
		, mime_type:str=None
		, name:str=None
	):
		self.fullpath = path_get(fullpath)
		assert file_exists(self.fullpath) \
		, lang.warn_file_not_exist.format(self.fullpath)
		self.use_save_to = use_save_to
		if not mime_type:
			mime_type = mimetypes.MimeTypes().guess_type(self.fullpath)[0]
			if not mime_type: mime_type = tcon.MIME_HTML
		self.mime_type = mime_type
		if not name: name = file_name(fullpath)
		self.name = name
def file_lock_wait(fullpath, wait_interval:str='100 ms'
, log:bool=False)->bool:
	'''
	Blocks execution until the file is available for reading.   
	The purpose is to wait for another process to
	stop writing to the file.  
	It's unreliable in many cases.  
	'''
	fullpath = path_get(fullpath)
	while True:
		try:

			open(fullpath, 'a').close()

			return True
		except PermissionError:
			if log:
				tprint('locked:', file_name(fullpath))
			else:
				pass
			time_sleep(wait_interval)
		except:
			tprint('unexpected exception:', file_name(fullpath), exc_text())
			return False

def file_relpath(fullpath, start)->str:
	r'''
	Returns a relative path.  

		asrt(
			file_relpath(r'c:\Windows\System32\calc.exe', r'c:\Windows')
			, 'System32\\calc.exe'
		)

	'''
	fullpath = path_get(fullpath).lstrip('\\\\?\\')
	start = path_get(start).lstrip('\\\\?\\')
	return os.path.relpath(fullpath, start=start)

def _file_name_pe(filename:str):
	for char, repl in _FORBIDDEN_DICT.items():
		filename = filename.replace(char, repl)
	return filename

def var_fpath(var)->str:
	r'''
	Full path of variable.

		var_set('_test', 1)
		tprint(var_fpath('_test'))
		asrt( var_del('_test'), True)

	'''
	if isinstance(var, str) and var[1] == ':': return var
	if is_iter(var):
		return os.path.join(APP_PATH, _VAR_DIR, *map(_file_name_pe, var) )
	else:
		return os.path.join(APP_PATH, _VAR_DIR, _file_name_pe(var) )

def var_open(var)->None:
	' Opens variable in default editor '
	win32api.ShellExecute(None, 'open', var_fpath(var)
	, None, None, 0)

def var_get(var, default=None, encoding:str='utf-8'
, as_literal:bool=False, globals:dict|None=None)->Any:
	r'''
	Gets the *disk variable*.  
	*as_literal* - converts to a literal (dict, list, tuple etc).
	Dangerous! - it's just `eval`, not `ast.literal_eval`!  
	*globals* - a dictionary with class names, for example for `datetime`:
	
		globals={'datetime': datetime}
	
	Examples:

		var_set('_test', 1)
		asrt( var_get('_test'), '1')
		asrt( var_get('_test', as_literal=True), 1 )
		asrt( var_del('_test'), True)

	'''
	fpath = var_fpath(var)
	try:
		content = file_read(fpath, encoding=encoding)
	except FileNotFoundError:
		return default
	if as_literal:
		return eval(content, globals) if content != '' else ''
	else:
		return content

def var_set(var, value, encoding:str='utf-8'):
	r'''
	Sets the disk variable.

		var_set('_test', 5)
		asrt( var_get('_test'), '5')
		asrt( var_del('_test'), True)
		var = ('file', 'c:\\pagefile.sys')
		var_set(var, 1)
		asrt( var_get(var, 1), '1' )
		asrt( var_del(var), True )

	'''
	fpath = var_fpath(var)
	value = str(value)
	try:
		file_write(fpath, content=value, encoding=encoding)
	except FileNotFoundError:
		os.makedirs(_VAR_DIR)
		file_write(fpath, content=value, encoding=encoding)

def var_del(var):
	r'''
	Deletes variable. Returns True if var exists.

		var_set('_test', 'a')
		asrt( var_del('_test'), True)
		
	'''
	fpath = var_fpath(var)
	try:
		os.remove(fpath)
		return True
	except FileNotFoundError:
		return False

def var_add(var, value, var_type=None
, encoding:str='utf-8'):
	r'''
	Adds the value to the previous value and returns the new value.

		asrt(var_add('_test', 5, var_type=int), 5)
		asrt(var_add('_test', 3),  8)
		asrt(var_del('_test'), True)

	'''
	prev = var_get(var, encoding=encoding, as_literal=True)
	if prev:
		if isinstance(prev, list):
			prev.append(value)
			value = prev
		elif isinstance(prev, int):
			value = prev + value
		elif isinstance(prev, set):
			prev.add(value)
			value = prev
		else:
			raise Exception('Wrong type of previous value')
	else:
		if var_type == set:
			value = set(value)
		elif var_type == int:
			value = int(value)
		else:
			value = [value]
	var_set(var, value, encoding=encoding)
	return value

def var_lst_get(var, default=None
, encoding:str='utf-8', com_str:str='#')->list:
	r'''
	Returns a list with text strings. Excludes empty strings
	and strings starting with *com_str*.  
	Reads files line by line, suitable for large files.  

		var_lst_set('_test', ['a', 'b'])
		asrt(var_lst_get('_test'), ['a', 'b'])
		var_lst_set('_test', map(str, (1, 2)))
		asrt(var_lst_get('_test'), ['1', '2'])
		asrt(var_del('_test'), True)
		asrt( var_lst_get('_test', ['not exists']), ['not exists'] )

	'''
	fpath = var_fpath(var)
	lst = []
	try:
		with open(fpath, encoding=encoding) as fd:
			for line in fd:
				line = line.strip()
				if line and not line.startswith(com_str):
					lst.append(line)
	except FileNotFoundError:
		return [] if default is None else default
	return lst

def var_mod(var)->datetime.datetime:
	r'''
	Returns the date when the file was last modified.
	'''
	fpath = var_fpath(var)
	return file_date_m(fpath)

def var_mod_dif(var, unit:str='sec')->int:
	r'''
	Returns how many time units have passed
	since the last change.

		asrt(var_mod_dif('_public_suffix_list', 'month'), 2, '<')

	'''
	return time_diff(var_mod(var), unit=unit)

def is_var_exists(var)->bool:
	r'''
	Is there a file with a variable?

		asrt( bmark(is_var_exists, (random_str()), b_iter=3), 45_000 )

	'''
	var = var_fpath(var)
	try:
		win32file.GetFileAttributesEx(var)
	except Exception as exc:
		if exc.args[0] == 2: return False
	return True

def var_lst_set(var, value, encoding:str='utf-8'):
	r'''
	Sets the disk list variable.
		var_lst_set('_test', ['a', 'b', 1])
		asrt( var_lst_get('_test'), ['a', 'b', '1'])
		asrt( var_del('_test'), True)

	'''
	var_set(var, value='\n'.join(map(str, value))
	, encoding=encoding)

def var_lst_add(var, value, encoding:str='utf-8')->list:
	r'''
	Adds the value to the list
	and returns the list.  

		var_lst_set('_test', 'ab')
		asrt( var_lst_add('_test', 'c'), ['a', 'b', 'c'] )
		asrt( var_del('_test'), True)

	'''
	lst = var_lst_get(var, encoding=encoding)
	lst.append(str(value))
	var_lst_set(var, value=lst, encoding=encoding)
	return lst

def var_lst_ext(var, value, encoding:str='utf-8')->list:
	r'''
	Expands the list with the values of *value*. Returns
	new list.

		var_lst_set('_test_ext', 'ab')
		asrt( var_lst_ext('_test_ext', 'cd'), ['a', 'b', 'c', 'd'] )
		asrt( var_del('_test_ext'), True)

	'''
	lst = var_lst_get(var, encoding=encoding)
	lst.extend(map(str, value))
	var_lst_set(var, lst, encoding=encoding)
	return lst

def file_drive(fullpath)->str:
	r'''
	Returns a drive letter in lowercase from a file name:

		asrt( file_drive(r'c:\\pagefile.sys'), 'c' )

	'''
	fullpath = path_get(fullpath)
	return os.path.splitdrive(fullpath)[0][:1].lower()

def file_conf_read(fullpath:str, encoding:str='utf-8'
, lowercase:bool=True, as_literal:bool=True)->dict:
	r'''
	Returns the contents of an config (.ini) file as a dictionary.
	
	*as_literal* - convert numeric values to numbers.
	
	Example (.ini file):

		[Section A]
		par1 = 1
		par2 = a string

	Result:

		{ 'Section A': {'par1': 1, 'par2': 'a string' } }

	'''
	fullpath = path_get(fullpath)
	parser = configparser.ConfigParser()
	if not lowercase: parser.optionxform = str
	parser.read(fullpath, encoding=encoding)
	confdict = { section: dict( parser.items(section) )
		for section in parser.sections() }
	if not as_literal: return confdict
	for sect_params in confdict.values():
		for param, value in sect_params.items():
			if value.isdigit(): sect_params[param] = int(value)
	return confdict
	
DriveIO = namedtuple(
	'DriveIO'
	, psutil._common.sdiskio._fields
	+ ('read_bytes_delta', 'write_bytes_delta', 'total_bytes_delta')
)

def drive_io(drive_num:int=-1)->Generator[DriveIO|dict, None, None]:
	r'''
	Returns a physical drive (not a volume/partition) I/O generator
	that returns a named tuples with counters. Example:

		dio = drive_io()
		qprint(next(dio)[0].read_bytes)
		time_sleep('1 sec')
		qprint(
			file_size_str(next(dio)[0].total_bytes_delta)
		)

	'''
	prev, prev_time = {}, 0
	while True:
		cur_time = time.time()
		delta_time = cur_time - prev_time
		cur = {}
		for drive, info in psutil.disk_io_counters(perdisk=True).items():
			drive = int(drive[13:])
			if (drive_num != -1) and drive_num != drive: continue
			if not drive in prev:
				prev[drive] = DriveIO(*info, 0, 0, 0)
			cur_rb, cur_wb = info.read_bytes, info.write_bytes
			delta_rb = int(
				(cur_rb - prev[drive].read_bytes) / delta_time
			)
			delta_wb = int(
				(cur_wb - prev[drive].write_bytes) / delta_time
			)
			prev[drive] = info
			cur[drive] = DriveIO(*info, delta_rb
			, delta_wb, delta_rb + delta_wb)
		prev_time = cur_time
		if drive_num != -1:
			yield cur[drive_num]
		else:
			yield cur

def path_rule(
	ex_ext:Iterable = tuple()
	, in_ext:Iterable = tuple()
	, ex_path:Iterable = tuple()
	, in_path:Iterable = tuple()
	, ex_dir:Iterable = tuple()
	, in_dir:Iterable = tuple()
	, ex_name:Iterable = tuple()
	, in_name:Iterable = tuple()
	, in_datem_aft:datetime.datetime|None = None
	, ex_datem_aft:datetime.datetime|None = None
	, in_datem_bef:datetime.datetime|None = None
	, ex_datem_bef:datetime.datetime|None = None
	, in_datec_aft:datetime.datetime|None = None
	, ex_datec_aft:datetime.datetime|None = None
	, in_datec_bef:datetime.datetime|None = None
	, ex_datec_bef:datetime.datetime|None = None
	, in_datea_aft:datetime.datetime|None = None
	, ex_datea_aft:datetime.datetime|None = None
	, in_datea_bef:datetime.datetime|None = None
	, ex_datea_bef:datetime.datetime|None = None
	, in_link:bool = False
	, ex_link:bool = False
	, in_rule:Callable|tuple|list|None = None
	, ex_rule:Callable|tuple|list|None = None
)->tuple[ list[Callable], list[Callable] ]:
	r'''
	Creates a list of rules (functions) to check
	a file or directory.  
	
	*in_\** - rule to include, *ex_\** - rule to exclude.  
	All rules are case-insensitive. All rules may be a string
	or a tuple/list of strings:  
	`ex_ext='py'`  
	`ex_ext=('py', 'pyc')`  
	Examples can be seen in `path_filter`.  


	*ex_ext*, *in_ext* - by extension.  
	*ex_path*, *in_path* - by any part of a full file path  
	*in_name*, *ex_name* - by part of a file name.  
	*ex_dir*, *in_dir* - by parent directory, i.e. the relative path.   

	*in_link*, *ex_link* - whether the folder or file is a link.  

	*in_rule*, *ex_rule* - user-defined rule(s) for a path. This
	should be a function that returns True or False when a match occurs.  

	File date variables.  
	Date value is a `datetime.datetime` or `datetime.timedelta`
	or a string based on `tcon.DATE_STR_HUMAN` pattern
	like that: '2023.02.12 0:0:0'  
	*datem*, *datea*, *datec* - date of modification, access, creation.  
	*in_datem_aft* - by date of modification (greater or equal)  
	*ex_datem_aft* - by date of modification (greater or equal)  

	Caveats:  
	
	- A file or directory will be excluded if `GetFileAttributes` fails
	to retrieve attributes (`in_link` for example).  

	'''
	
	ex_rules = list()
	in_rules = list()
	if ex_ext:
		if isinstance(ex_ext, str): ex_ext = (ex_ext, )
		ex_ext = set((e.lower() for e in ex_ext))
		ex_rules.append(lambda p: any(
			os.path.splitext(p)[1][1:].lower() == e
			for e in ex_ext
		))
	if in_ext:
		if isinstance(in_ext, str): in_ext = (in_ext, )
		in_ext = set((e.lower() for e in in_ext))
		in_rules.append(lambda p: any(
			os.path.splitext(p)[1][1:].lower() == e
			for e in in_ext
		))
	if ex_path:
		if isinstance(ex_path, str): ex_path = (ex_path, )
		ex_path = set((e.lower() for e in ex_path))
		ex_rules.append(lambda p: any(
			e in p.lower()
			for e in ex_path
		))
	if in_path:
		if isinstance(in_path, str): in_path = (in_path, )
		in_path = set((e.lower() for e in in_path))
		in_rules.append(lambda p: any(
			e in p.lower()
			for e in in_path
		))
	if ex_name:
		if isinstance(ex_name, str): ex_name = (ex_name, )
		ex_name = set((np.lower() for np in ex_name))
		ex_rules.append(lambda p: any(
			np in os.path.basename(p).lower()
			for np in ex_name
		))
	if in_name:
		if isinstance(in_name, str): in_name = (in_name, )
		in_name = set((np.lower() for np in in_name))
		in_rules.append(lambda p: any(
			np in os.path.basename(p).lower()
			for np in in_name
		))
	if ex_dir:
		if isinstance(ex_dir, str): ex_dir = (ex_dir, )
		ex_dir = set((e.lower().lstrip('\\') for e in ex_dir))
		for ex in ex_dir:
			assert not ':' in ex, 'the ex_dir must contain relative paths'
		ex_rules.append(lambda p: any(
			p.lower().startswith(e)
			for e in ex_dir
		))
	if in_dir:
		if isinstance(in_dir, str): in_dir = (in_dir, )
		in_dir = set((e.lower().lstrip('\\') for e in in_dir))
		for ex in in_dir:
			assert not ':' in ex, 'the in_dir must contain relative paths'
		in_rules.append(lambda p: any(
			p.lower().startswith(e)
			for e in in_dir
		))
	if in_link or ex_link:
		(in_rules if in_link else ex_rules).append( lambda p: (
			max(win32file.GetFileAttributes(p), 0) & _FILE_ATTRIBUTE_REPARSE_POINT
			) == _FILE_ATTRIBUTE_REPARSE_POINT
		)
	if in_rule:
		in_rules.extend( in_rule if is_iter(in_rule) else (in_rule,) )
	if ex_rule:
		ex_rules.extend( ex_rule if is_iter(ex_rule) else (ex_rule,) )
	for val, time_att, is_inc, is_bef in (
		(ex_datem_aft, 'st_mtime', False, False)
		, (ex_datem_bef, 'st_mtime', False, True)
		, (in_datem_aft, 'st_mtime', True, False)
		, (in_datem_bef, 'st_mtime', True, True)
		, (ex_datec_aft, 'st_ctime', False, False)
		, (ex_datec_bef, 'st_ctime', False, True)
		, (in_datec_aft, 'st_ctime', True, False)
		, (in_datec_bef, 'st_ctime', True, True)
		, (ex_datea_aft, 'st_atime', False, False)
		, (ex_datea_bef, 'st_atime', False, True)
		, (in_datea_aft, 'st_atime', True, False)
		, (in_datea_bef, 'st_atime', True, True)
	):
		if not val: continue
		lst = in_rules if is_inc else ex_rules
		assert isinstance(val, (str, datetime.datetime,  datetime.timedelta)) \
			, 'file time must be a string or datetime or timedelta'
		if isinstance(val, str):
			val = time_from_str(val, template=tcon.DATE_STR_HUMAN)
		elif isinstance(val, datetime.datetime):
			pass
		elif isinstance(val, datetime.timedelta):
			val = datetime.datetime.now() - val
		else:
			raise Exception('wrong date rule')
		tstamp = val.timestamp()
		if is_bef:
			lst.append(
				lambda p, a=time_att, t=tstamp: getattr( \
					os.stat(path_long(p)), a \
				) <= t
			)
		else:
			lst.append(
				lambda p, a=time_att, t=tstamp: getattr( \
					os.stat(path_long(p)), a \
				) >= t
			)
	return in_rules, ex_rules

def _path_match(path:str, in_rules:list, ex_rules:list)->bool:
	r'''
	Returns True if path matches rules from the `path_rule`.

		from plugins.plugin_filesystem import _path_match
		inr, exr = path_rule(in_ext='py', ex_ext='pyc')
		asrt( _path_match(r'crontab.py', inr, exr), True )
		asrt( _path_match(r'crontab.pyc', inr, exr), False )
		inr, exr = path_rule(ex_path='.pyc')
		asrt( _path_match(r'crontab.pyc', inr, exr), False )
		latest = tuple(dir_files('plugins'))

	'''
	return (
		(all(r(path) for r in in_rules) if in_rules else True)
		and
		not (any(r(path) for r in ex_rules) if ex_rules else False)
	)

def path_filter(
	paths:Iterable
	, **rules
)->Iterator[str]:
	r'''
	Filters a list of files by criteria from the `path_rule`

		pf = path_filter
		files = tuple( dir_files((app_dir(), 'plugins')
		, name_only=True, subdirs=False) )
		asrt( tuple( pf(files, ex_dir='__pycache__'))[0], 'constants.py')
		asrt( tuple( pf(files, ex_ext='pyc'))[0], 'constants.py')
		asrt( tuple( pf(files, ex_ext='pyc', ex_path='_TOOLS_patc'))[-1], 'winapi.py')
		asrt( tuple( pf(files, ex_ext=('pyc', 'py') ) ), ())
		asrt( tuple( pf(files, in_ext='txt' ) ), ())
		asrt( tuple( pf(files, in_ext='py', ex_path='_TOOLS_patc'))[-1], 'winapi.py')
		asrt( tuple( pf(files, in_path='constants.py'))[0], 'constants.py')
		asrt( tuple( pf(files, in_name='crypt') )[0], 'plugin_crypt.py')
		asrt(
			tuple( pf(files, in_ext='py', ex_name=('plug', 'const')) )[0]
			, r'tools.py'
		)
		asrt(
			tuple( pf(files, in_rule=lambda p: 'mail' in p ) )
			, ('plugin_mail.py',)
		)
		asrt(
			tuple( pf(files, ex_rule=lambda p: '_' in p ) )
			, ('constants.py', 'tools.py', 'winapi.py')
		)
		asrt(
			tuple( pf(files, in_rule=(
				lambda p: '_' in p
				, lambda p: 'mail' in p
			) ) )
			, ('plugin_mail.py',)
		)
		files = tuple( dir_files((app_dir(), 'plugins')
		, name_only=False, subdirs=False) )
		asrt(
			tuple( pf(files, in_datem_aft=datetime.datetime(2030, 1, 1), ) )
			, ()
		)
		asrt(
			tuple( pf(files, ex_datem_aft=datetime.datetime(2020, 12, 24), ) )
			, ()
		)
		asrt(
			tuple( pf(files, in_datem_aft='2030.1.1 0:0:0', ) )
			, ()
		)
		asrt(
			tuple( pf(files, ex_datem_aft='2020.12.24 0:0:0', ) )
			, ()
		)
		asrt(
			tuple( pf(files, in_ext='py', in_datem_bef='2020.12.24 0:0:0', ) )
			, ()
		)
		asrt(
			tuple( pf( (r'c:\Documents and Settings',) , in_link=True) )
			, (r'c:\Documents and Settings',)
		)
		asrt(
			tuple( pf( (r'c:\Documents and Settings', r'c:\Users') , ex_link=True) )
			, (r'c:\Users',)
		)

	'''
	in_rules, ex_rules = path_rule(**rules)
	for path in paths:
		if _path_match(path=path, in_rules=in_rules, ex_rules=ex_rules):
			yield path


class DirSync:
	r'''
	One-way directory synchronization.
	'''
	

	def __init__(
		self
		, src_dir:str
		, dst_dir:str
		, report:bool=False
		, max_table_width:int=0
		, **rules
	):
		r'''
		*report* - print every file copy/del operation.
		'''
		self._src_dir = dir_slash(path_get(src_dir))
		self._dst_dir = dir_slash(path_get(dst_dir))
		self._report = report
		self._rules = rules
		self._src_files = set()
		self._dst_files = set()
		self._src_dirs = set()
		self._dst_dirs = set()
		self._new_files = set()
		self._src_only_files = set()
		self._dst_only_files = set()
		self._max_table_width:int=max_table_width
		self.errors = dict()
		self._start:dtime = dtime.min
		self.duration:str = ''
	
	def _walk(self):
		' Reads contens of src and dst directories '
		start = dtime.now()
		self._src_files = set()
		self._src_dirs = set()
		self._dst_files = set()
		self._dst_dirs = set()
		for dirpath, dirnames, filenames in os.walk(
			path_long(self._src_dir, force=True)
		):
			for d in dirnames:
				self._src_dirs.add(
					os.path.join(dirpath[4:], d)
				)
			for f in filenames:
				self._src_files.add(
					os.path.join(dirpath[4:], f)
				)
		for dirpath, dirnames, filenames in os.walk(
			path_long(self._dst_dir, force=True)
		):
			for d in dirnames:
				self._dst_dirs.add(
					os.path.join(dirpath[4:], d)
				)
			for f in filenames:
				self._dst_files.add(
					os.path.join(dirpath[4:], f)
				)
		if is_con(): qprint('walk done in', time_diff_human(start))

	def compare(self)->bool:
		r'''
		Reads the directories and makes a comparison.
		'''
		self._start = dtime.now()
		cstart = dtime.now()
		self.errors = dict()
		self._walk()
		slen = len(self._src_dir)
		dlen = len(self._dst_dir)
		self._src_files = set( (p[slen:] for p in self._src_files) )
		self._dst_files = set( (p[dlen:] for p in self._dst_files) )
		if self._rules:
			rstart = dtime.now()
			self._src_files = set(path_filter(
				paths=self._src_files
				, **self._rules
			))
			if is_con(): qprint('file rules done in', time_diff_human(rstart))
		self._src_only_files = self._src_files - self._dst_files
		self._dst_only_files = self._dst_files - self._src_files
		self._src_dirs = set( (p[slen:] for p in self._src_dirs) )
		self._dst_dirs = set( (p[dlen:] for p in self._dst_dirs) )
		if self._rules:
			rstart = dtime.now()
			self._src_dirs = set(path_filter(
				paths=self._src_dirs
				, **self._rules
			))
			if is_con(): qprint('dir rules done in', time_diff_human(rstart))
		self._dst_only_dirs = self._dst_dirs - self._src_dirs
		self._get_new_files()
		if is_con(): qprint('compare done in', time_diff_human(cstart))
		return len(self.errors) == 0
	
	def _log(self, oper:str, path:str):
		' Print current file operation '
		if not self._report: return
		qprint(path_short( f'sync {oper}: {path}'))
	
	def _get_new_files(self):
		start = dtime.now()
		self._new_files = set()
		for rpath in (self._src_files.intersection(self._dst_files)):
			try:
				src_datem = win32file.GetFileAttributesEx(
					path_long(self._src_dir + rpath)
				)[3].replace(microsecond=0)
				dst_datem = win32file.GetFileAttributesEx(
					path_long(self._dst_dir + rpath)
				)[3].replace(microsecond=0)
				if src_datem > dst_datem: self._new_files.add(rpath)
			except:
				if is_con():
					qprint(
						str_short('datem error: ' + exc_text(with_file=False))
					)
				if is_con():
					qprint(str_short(
						'datem error: ' + exc_text(with_file=False)
						, _TERMINAL_WIDTH
					))
				self.errors[rpath] = 'mdate error'
		if is_con(): qprint('new files done in', time_diff_human(start))

	def _copy(self):
		r''' Copy unique and new files from src to dst '''
		for fileset in self._src_only_files, self._new_files:
			for rpath in fileset:
				self._log('copy', rpath)
				for _ in (1, 2):
					try:
						win32api.CopyFile(
							path_long(self._src_dir + rpath)
							, path_long(self._dst_dir + rpath)
						)
					except win32api.error as err:
						if err.winerror == 3:
							try:
								os.makedirs(file_dir( self._dst_dir + rpath ))
							except:
								self.errors[rpath] = 'dir create'
								break
							else:
								continue
						if is_con():
							qprint(str_short(
								'copy err ('
								+ path_short(rpath, 40) + '): '
								+ exc_text(with_file=False)
							))
						self.errors[rpath] = 'copy'
						break
	
	def _delete_dirs(self):
		r'''
		Deletes dst-only directories and removes
		their files from self._dst_only_files.
		'''
		errors = set()
		for rpath in self._dst_only_dirs:
			err = dir_delete((self._dst_dir, rpath))
			self._log('del dir', rpath)
			if err:
				errors.add(rpath)
				if is_con():
					qprint(path_short(f'dir del err {len(err)}: {rpath}'))
				self.errors[rpath] = f'dir del {len(err)}'
		del_dirs = self._dst_only_dirs - errors
		self._dst_only_files = set(
			f for f in self._dst_only_files
			if not any(f.startswith(d) for d in del_dirs)
		)

	def _delete_files(self):
		' Delete files that do not exist in the src '
		for rpath in self._dst_only_files:
			if (err := file_delete((self._dst_dir, rpath))) == 0: 
				self._log('del file', rpath)
			else:
				if is_con():
					qprint(str_short('file del err: '
					+ exc_text(with_file=False) ) )
				self.errors[rpath] = f'file del {err}'

	def print_diff(self):
		r'''
		Print a table with the difference between
		the directories.
		'''
		qprint('\nDirSync:', self._src_dir, '->', self._dst_dir)
		table = [('Diff', 'Path')]
		table.extend( (('src only', p) for p in self._src_only_files) )
		table.extend( (('dst only', p) for p in self._dst_only_files) )
		table.extend( (('dst only', p) for p in self._dst_only_dirs) )
		table.extend( (('new', p) for p in self._new_files) )
		table_print(
			table
			, use_headers=True
			, max_table_width=self._max_table_width
			, sorting=(0, 1)
			, trim_func=path_short
		)
		qprint(
			f'All done in {self.duration}'
			, f'\nsrc files: {int_str(len(self._src_files))}'
			, f'\nsrc only files: {int_str(len(self._src_only_files))}'
			, f'\ndst only files: {int_str(len(self._dst_only_files))}'
			, f'\ndst only dirs: {int_str(len(self._dst_only_dirs))}'
			, f'\nnew files: {int_str(len(self._new_files))}'
			, f'\nerrors: {int_str(len(self.errors))}\n'
		)
	
	def save_diff(self, dst_file:str='')->str:
		' Save the difference between directories to a file '
		if not dst_file: dst_file=temp_file(prefix='dirsync_'
		, suffix='.txt')
		content = '\n'.join(
			f'src only\t{p}' for p in sorted(self._src_only_files)
		)
		content += '\n'.join(
			f'dst only\t{p}' for p in sorted(self._dst_only_files)
		)
		content += '\n'.join(
			f'dst only\t{p}' for p in sorted(self._dst_only_dirs)
		)
		file_write(dst_file, content=content)
		return dst_file
	
	def print_errors(self):
		table = [('Error', 'Path')]
		for path, err in self.errors.items():
			table.append((err, path))
		table_print(
			table
			, use_headers=True
			, max_table_width=self._max_table_width
			, sorting=(0, 1)
			, trim_func=path_short
		)
	
	def sync(self)->bool:
		' Perform synchronization '
		start = time_now()
		self.errors = dict()
		self._delete_dirs()
		self._delete_files()
		self._copy()
		self.duration = time_diff_human(self._start)
		if is_con(): qprint('sync done in', time_diff_human(start))
		return len(self.errors) == 0


def dir_sync(src_dir, dst_dir, report:bool=False
, **rules)->dict:
	r'''
	One-way directory synchronization.  
	For *rules* see the `path_rule`.  
	Returns dict with errors: `{'path\\file.exe': 'copy error', ...}`  
		
		src, dst = dir_test(), temp_dir('rnd')
		dir_sync(src, dst)
		asrt(
			tuple( dir_files(src, name_only=True) )
			, tuple( dir_files(dst, name_only=True) )
		)
		dir_delete(src)
		dir_delete(dst)

	'''
	sync = DirSync(src_dir=src_dir, dst_dir=dst_dir
	, **rules)
	sync.compare()
	sync.sync()
	if report: sync.print_diff()
	if sync.errors and report: sync.print_errors()
	return sync.errors.copy()



class DirDup:
	r'''
	First we find groups of files with the same size
	, then we look for unique ones within those groups.

	Example:

		ddup = DirDup(r'c:\folder', DirDup.ALGO_SIZE, in_ext='jpg')
		ddup.find_dup()
		ddup.print_dup()
	
	If you choose to search by hash (or mdate, cdate) of the beginning
	or the whole file the files are grouped by size first (it's cheap)
	and hashing is performed only within this group of files with the
	same size.

	The result of work is the `dups` attribute, which is a list of tuples
	with property dictionaries of found duplicates.  
	For example, you can loop through this tuple list and delete (recycle)
	files that are not the oldest or newest:

		for dups in ddup.dups:
			for dup in dups:
				if dup['is_cnewest']: continue
				file_recycle(dup['fpath'])

	or just use `clean` method:

		ddup.clean(leave='coldest')

	'''
	ALGO_SIZE = 'Size'
	ALGO_MDATE = 'Modification date'
	ALGO_CDATE = 'Creation date'
	ALGO_HASH_BEG = 'Hash of the beginning'
	ALGO_HASH_FULL = 'Hash of the whole'

	def __init__(self, src_dir:str|tuple|list, algo:str
	, hash_size_limit_perc:int=5, **rules)->None:
		assert algo in (self.ALGO_SIZE, self.ALGO_HASH_BEG
		, self.ALGO_HASH_FULL, self.ALGO_MDATE, self.ALGO_CDATE), 'unknown algorithm'
		self._src_dirs:tuple = (src_dir,) if isinstance(src_dir, str) else src_dir
		self._algo:str = algo
		self._dtype = 'cdate' if self._algo == self.ALGO_CDATE else 'mdate'
		self._hash_size_limit_perc:int = hash_size_limit_perc
		self._rules:dict = rules
		self._files:dict = dict()
		self._dups:tuple = tuple()
		self._buf_size:int = 4096

	def _file_md5(self, fpath:str, fsize:int)->str:
		hsh = hashlib.md5()
		chunk_limit = 0
		if self._algo == self.ALGO_HASH_BEG:
			chunk_limit = fsize * self._hash_size_limit_perc / 100 / self._buf_size
		chunk_cnt = 0.0
		with open(fpath, 'rb') as fd:
			for chunk in iter(lambda: fd.read(self._buf_size), b''):
				chunk_cnt += 1.0
				hsh.update(chunk)
				if chunk_limit and (chunk_cnt >= chunk_limit): break
		return hsh.hexdigest()

	def scan(self):
		self._files = dict()
		tstart = time_now()
		for d in self._src_dirs:
			for fpath in dir_files(d, **self._rules):
				self._files[fpath] = {'is_unique': True, 'is_cnewest': False
				, 'is_coldest': False, 'is_mnewest': False, 'is_moldest': False}
				att = win32file.GetFileAttributesEx(fpath)
				self._files[fpath]['fpath'] = fpath
				self._files[fpath]['size'] = att[4]
				self._files[fpath]['mdate'] = att[3]
				self._files[fpath]['cdate'] = att[1]
		if is_con(): qprint(f'scan done in {time_diff_human(tstart)}')

	def find_dup(self):
		if not self._files: self.scan()
		self._sizes = dict()
		self._dates = dict()
		tstart = time_now()
		for fpath, props in self._files.items():
			if props['size'] in self._sizes:
				self._sizes[props['size']].append(fpath)
			else:
				self._sizes[props['size']] = [fpath]
			if self._algo in (self.ALGO_MDATE, self.ALGO_CDATE):
				if props[self._dtype] in self._dates:
					self._dates[props[self._dtype]].append(fpath)
				else:
					self._dates[props[self._dtype]] = [fpath]
		if self._algo == self.ALGO_SIZE:
			for fpaths in self._sizes.values():
				if len(fpaths) == 1: continue
				for fpath in fpaths:
					self._files[fpath]['is_unique'] = False
			self._collect_dups()
			if is_con(): qprint(f'done in {time_diff_human(tstart)}')
			return
		for size, fpaths in self._sizes.items():
			if len(fpaths) == 1: continue
			if self._algo in (self.ALGO_MDATE, self.ALGO_CDATE):
				dates = tuple(self._files[f][self._dtype].timestamp() for f in fpaths)
				for fpath in fpaths:
					self._files[fpath]['is_unique'] = dates.count(
						self._files[fpath][self._dtype].timestamp()
					) == 1
			else:
				hashes = list()
				for fpath in fpaths:
					hsh = self._file_md5(fpath, fsize=size)
					self._files[fpath]['hash'] = hsh
					hashes.append(hsh)
				for fpath in fpaths:
					self._files[fpath]['is_unique'] = hashes.count(
						self._files[fpath]['hash']
					) == 1
		self._collect_dups()
		if is_con(): qprint(f'done in {time_diff_human(tstart)}')
	
	def _collect_dups(self):
		r'''
		Makes a convient dictionary with duplicates for further user actions.  
		Finds newest and oldest files.  
		'''
		self.dups = []
		for fpaths in self._sizes.values():
			if len(fpaths) == 1: continue
			dups:list = []
			for fpath in fpaths:
				props = self._files[fpath]
				if not props['is_unique']: dups.append(props)
			if not dups: continue
			dups.sort(key=itemgetter('cdate'))
			dups[0]['is_cnewest'] = True
			dups[-1]['is_coldest'] = True
			dups.sort(key=itemgetter('mdate'))
			dups[0]['is_mnewest'] = True
			dups[-1]['is_moldest'] = True
			self.dups.append(tuple(d for d in dups))
	
	def print_all(self, fullname:bool=False):
		' Print all files '
		table = [('File', 'Unique', self._algo)]
		for fpath, props in self._files.items():
			name = fpath if fullname else file_name(fpath)
			if self._algo == self.ALGO_SIZE:
				sign = props['size']
			elif self._algo in (self.ALGO_MDATE, self.ALGO_CDATE):
				sign = props[self._dtype].strftime(tcon.DATE_STR_HUMAN)
			else:
				sign = props.get('hash', None)
			table.append((name, str(props['is_unique']), sign))
		table_print(table, use_headers=True, trim_col=0
		, trim_func=path_short, sorting=(1, 0))

	def print_dup(self, fullname:bool=False):
		' Print duplicates only '
		dtype = 'c' if self._dtype == 'cdate' else 'm'
		table = [('File', f'Is {dtype}New', f'Is {dtype}Old', self._algo)]
		for size, fpaths in self._sizes.items():
			if len(fpaths) == 1: continue
			for fpath in fpaths:
				name = fpath if fullname else file_name(fpath)
				props = self._files[fpath]
				if props['is_unique']: continue
				if self._algo == self.ALGO_SIZE:
					sign = size
				elif self._algo in (self.ALGO_MDATE, self.ALGO_CDATE):
					sign = props[self._dtype].strftime(tcon.DATE_STR_HUMAN)
				else:
					sign = props['hash']
				table.append((
					name
					, str(props[f'is_{dtype}newest'])
					, str(props[f'is_{dtype}oldest'])
					, sign
				))
		table_print(table, use_headers=True, trim_col=0
		, trim_func=path_short, sorting=(-1, 0))
		size, count = 0, 0
		for dups in self.dups:
			for dup in dups:
				size += dup['size']
				count += 1
		qprint(f'Total: {count} duplicates, {file_size_str(size)}\n')

	def clean(self, leave:str, recycle:bool=True)->tuple:
		r'''
		Deletes all but one duplicate.  
		Returns (count, size) of deleted files.  
		*leave* - parameter determines which file should
		not be deleted. Examples: 'cnewest', 'mnewest'
		, 'coldest', 'moldest' (like in `scan` method).  
		'''
		dfunc = file_recycle if recycle else file_delete
		count, size = 0, 0
		for dups in self.dups:
			for dup in dups:
				if dup[f'is_{leave}']: continue
				count += 1
				size += dup['size']
				dfunc(dup['fpath'])
		tdebug(f'cleaned: {count}, {file_size_str(size)}')
		return count, size

def dir_dedup(src_dir:str|tuple|list, leave:str
, algo:str=DirDup.ALGO_HASH_BEG, print_dup:bool=True
, recycle:bool=True, **rules)->tuple:
	r'''
	Deletes duplicate files from the specified folder(s).  
	A wrapper for the `DirDup` class.  
	Returns the number of deleted files and their size.  
	*leave* - 'cnewest', 'mnewest', 'coldest', 'moldest'  
	*rules* - rules for the `path_rule` function  
	'''
	ddup = DirDup(src_dir=src_dir, algo=algo, **rules)
	ddup.find_dup()
	if print_dup: ddup.print_dup()
	return ddup.clean(leave=leave, recycle=recycle)

def rec_bin_size(drive:str|None=None)->tuple:
	r'''
	Retrieves the total size and number of items
	in the Recycle Bin for a specified drive.  
	'''
	return shell.SHQueryRecycleBin(drive)

def rec_bin_purge(drive:str=None, progress:bool=False, sound:bool=True):
	r'''
	Clears the recycle bin.
		rec_bin_purge('c')
		rec_bin_purge()

	'''
	flags = shellcon.SHERB_NOCONFIRMATION
	if not progress: flags |= shellcon.SHERB_NOPROGRESSUI
	if not sound: flags |= shellcon.SHERB_NOSOUND
	if drive: drive = drive[0] + ':'
	try:
		shell.SHEmptyRecycleBin(None, drive, flags)
	except shell.error as e:
		if e.args[0] == -2147418113:
			tdebug(f'recycle bin is empty')
		else:
			raise

def path_is_link(fullpath)->bool:
	r'''
	Returns `True` if the path is a link.  
	Returns `False` even if the file does not exist.  

		asrt( path_is_link(r'c:\Documents and Settings'), True )
		asrt( path_is_link(r'c:\pagefile.sys'), False )
		asrt( bmark(path_is_link, ('c:\\Documents and Settings',)), 25_000 )
		
	'''
	fpath = path_get(fullpath)
	if (atts := win32file.GetFileAttributes(fpath)) == -1: return False
	return (atts & _FILE_ATTRIBUTE_REPARSE_POINT) \
	== _FILE_ATTRIBUTE_REPARSE_POINT

def dir_junc(src_path, dst_path):
	r'''
	Creates a junction link to a directory.  
	Only for local paths.  

		td = dir_test()
		tdj = file_name_add(td, ' junc')
		dir_junc(td, tdj)
		asrt( dir_exists(tdj), True )
		dir_delete(td)
		asrt( dir_exists(tdj), False )
		dir_delete(tdj)

	'''
	src_path = path_get(src_path)
	dst_path = path_get(dst_path)
	CreateJunction(src_path, dst_path)




if __name__ != '__main__': patch_import()