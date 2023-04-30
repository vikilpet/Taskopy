r'''
Naming convention:
fullpath, fpath, fp - full path of a file (r'd:\soft\taskopy\crontab.py')
fname - file name only ('crontab.py')
relpath - relative path ('taskopy\crontab.py')
'''
from ctypes import WinError
import os
import stat
import time
import glob
from contextlib import contextmanager
from collections import namedtuple
import csv
import random
import pyodbc
import mimetypes
import zipfile
from zlib import crc32
import tempfile
import datetime
import win32con
import win32com
import win32print
import hashlib
import pythoncom
import base64
from typing import Callable, Iterator, List, Union \
, Iterable, Tuple
import psutil
import win32file

import win32api
from win32com.shell import shell, shellcon
from pathlib import Path
import shutil
import configparser
from .tools import _APP_PATH, APP_NAME, exc_text, random_str, table_print, tdebug, patch_import, time_diff_str, time_now \
, time_sleep, dev_print, tprint, is_iter, time_diff, time_from_str
try:
	import constants as tcon
except ModuleNotFoundError:
	import plugins.constants as tcon

_SIZE_UNITS = {'tb': 1_099_511_627_776, 'gb': 1_073_741_824
	, 'mb': 1_048_576, 'kb': 1024, 'b': 1}
_FORBIDDEN_CHARS = '<>:"\\/|?*'
_FORBIDDEN_DICT = dict(
	**{chr(d) : '%' + hex(d)[2:] for d in range(32)}
	, **{ c : '%' + hex(ord(c))[2:].upper() for c in _FORBIDDEN_CHARS}
)
_VAR_DIR = 'resources\\var'

def _dir_slash(dirpath:str)->str:
	''' Adds a trailing slash if it's not there. '''
	if dirpath.endswith('\\'): return dirpath
	return dirpath + '\\'

def path_get(fullpath, max_len:int=0
, trim_suf:str='...')->str:
	r'''
	Join list of paths and optionally
	fix long path. Fill environment variables ('%APPDATA%').  
	Special variable (os.getcwd): %taskopy%  
	*max_len* - if set, then limit the
	maximum length of the full path.  

		path = path_get(('%appdata%', 'Media Center Programs'))
		tass( dir_exists(path), True)
		path = (r'c:\Windows', '\\notepad.exe')
		path2 = r'c:\Windows\notepad.exe'
		tass( os.path.join(*path), r'c:\notepad.exe' )
		tass( path_get( path ), path2 )
		path = (r'c:\Windows\\', 'notepad.exe')
		tass( path_get( path ), path2 )
		path = (r'c:\Windows\\', '\\notepad.exe')
		tass( path_get( path ), path2 )
		tass( path_get( path, 20 ), r'c:\Windows\no....exe' )
		tass( path_get(r'c:\Windows\\'), 'c:\\Windows\\')
		tass( file_exists('%taskopy%\\crontab.py'), True)

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
			fullpath = os.path.join( _APP_PATH, rem )
		else:
			fullpath = os.path.join( os.getenv(env_var), rem )
	if max_len and (len(fullpath) > max_len):
		fname, ext = os.path.splitext( os.path.basename(fullpath) )
		fdir = os.path.dirname(fullpath)
		limit = len(fullpath) - max_len + len(trim_suf)
		fullpath = os.path.join(
			fdir, fname[:-limit] + trim_suf + ext
		)
	elif (
		len(fullpath) > 255
		and not fullpath.startswith('\\\\?\\')
		and (
			fullpath[1:3] == ':\\'
			or fullpath.startswith('\\\\')
		)
	):
		return '\\\\?\\' + fullpath
	return fullpath

def file_read(fullpath, encoding:str='utf-8', errors:str=None)->str:
	'''
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
	Saves content to a file.  
	Creates file if the fullpath doesn't exist
	and creates intermediate directories  
	If fullpath is '' or None - uses `temp_file()`.  
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
	''' Renames path.
		dest - fullpath or just new file name
		without parent directory.
		overwrite - overwrite destination file
		if exists.
		Returns destination.
		Example:

			file_rename(r'd:\\IMG_123.jpg', 'my cat.jpg')
			>'d:\\my cat.jpg'
			
	'''
	fullpath = path_get(fullpath)
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

def dir_rename(fullpath, dest
, overwrite:bool=False)->str:
	'''
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

def file_log(fullpath, message:str, encoding:str='utf-8'
, time_format:str='%Y.%m.%d %H:%M:%S'):
	''' Writes message to log '''
	fullpath = path_get(fullpath)
	with open(fullpath, 'at+', encoding=encoding) as f:
		f.write(time.strftime(time_format) + '\t' + message + '\n')



def file_copy(fullpath, destination)->str:
	'''
	Copies file to destination.  
	Destination may be a full path or directory.  
	Returns destination full path.  
	If destination file exists it will be overwritten.  
	If destination is a folder, subfolders will
	be created if they don't exist.  

		tf, td = temp_file(suffix='.txt'), temp_dir('test_fc')
		file_write(tf, 't')
		tass(
			file_copy(tf, (td, file_name(tf) ))
			, os.path.join(td, file_name(tf) )
		)
		tass( file_copy(tf, td), os.path.join(td, file_name(tf) ) )
		tass(
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
		os.makedirs(
			os.path.dirname(destination)
		)
		win32api.CopyFile(fullpath, destination)
	return destination

def file_append(fullpath, content:str, encoding:str='utf-8')->str:
	''' Append content to a file. Creates fullpath
		if not specified.
		Returns the fullpath.
	'''
	if fullpath:
		fullpath = path_get(fullpath)
	else:
		fullpath = temp_file()
	with open(fullpath, 'a+', encoding=encoding) as fd:
		fd.write(content)
	return fullpath

def file_move(fullpath, destination)->str:
	''' Move file to destination.
		Returns full path of destination file.
		Destination may be fullpath or folder name.
		If destination path exist it will be overwritten.
	'''
	fullpath = path_get(fullpath)
	destination = path_get(destination)
	if os.path.isdir(destination):
		new_fullpath = _dir_slash(destination) \
			+ os.path.basename(fullpath)
	else:
		new_fullpath = destination
	try:
		file_delete(new_fullpath)
	except FileNotFoundError:
		pass
	shutil.move(fullpath, new_fullpath)
	return new_fullpath

def file_delete(fullpath):
	''' Deletes the file. '''
	fullpath = path_get(fullpath)
	try:
		os.remove(fullpath)
	except PermissionError:
		try:
			os.chmod(fullpath, stat.S_IWRITE)
			os.remove(fullpath)
		except Exception as e:
			tdebug(f'file_delete error: {e}')
	except FileNotFoundError:
		tdebug('not found')
		pass

def file_recycle(fullpath, silent:bool=True)->bool:
	''' Move file to the recycle bin
		silent - do not show standard windows
		dialog to confirm deletion.
		Returns True on successful operation.
	'''
	fullpath = path_get(fullpath)
	flags = shellcon.FOF_ALLOWUNDO
	if silent:
		flags = flags | shellcon.FOF_SILENT | shellcon.FOF_NOCONFIRMATION
	result = shell.SHFileOperation(
		(
			0
			, shellcon.FO_DELETE
			, fullpath
			, None
			, flags
			, None
			, None
		)
	)
	return result[0] <= 3

def dir_copy(fullpath, destination:str
, symlinks:bool=False)->int:
	''' Copy a folder with all content to a new location.
		Returns number of errors.
	'''
	fullpath = path_get(fullpath)
	destination = path_get(destination)
	err = 0
	try:
		shutil.copytree(fullpath, destination, symlinks=symlinks)
	except FileExistsError:
		pass
	except Exception as e:
		err += 1
		print(f'dir_copy error: {repr(e)}')
	return err

def dir_create(fullpath=None)->str:
	''' Creates new dir and returns full path.
		If fullpath=None then creates temporary directory.
	'''
	fullpath = path_get(fullpath)
	if not fullpath: return temp_dir('temp')
	fullpath = fullpath.rstrip('.').rstrip(' ')
	try:
		os.makedirs(fullpath)
	except FileExistsError: pass
	return fullpath

def dir_delete(fullpath):
	''' Deletes folder with it's contents '''
	fullpath = path_get(fullpath)
	try:
		shutil.rmtree(fullpath
		, onerror=lambda func, path, exc: file_delete(path))
		return fullpath
	except FileNotFoundError:
		return fullpath

def dir_exists(fullpath)->bool:
	return os.path.isdir( path_get(fullpath) )

def file_exists(fullpath)->bool:
	return os.path.isfile( path_get(fullpath) )

def path_exists(fullpath)->bool:
	''' Check if directory or file exist '''
	fullpath = path_get(fullpath)
	p = Path(fullpath)
	return p.exists()

def file_size(fullpath, unit:str='b')->int:
	r'''
	Gets the file size in the specified units.  

		fpath = r'c:\Windows\System32\notepad.exe' # on SSD
		benchmark(win32file.GetFileAttributesEx, fpath)
		benchmark(os.stat, fpath)

	'''
	fullpath = path_get(fullpath)
	e = _SIZE_UNITS.get(unit.lower(), 1)
	return win32file.GetFileAttributesEx(fullpath)[4] // e

def file_size_str(fullpath)->str:
	'''
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
	''' Returns file extension in lower case
		without dot.
	'''
	fullpath = path_get(fullpath)
	ext = os.path.splitext(fullpath)[1].lower()
	if ext == '': return ext
	return ext[1:]

def file_basename(fullpath)->str:
	r'''
	Returns basename: file name without 
	parent folder and extension. Example:

		tass( file_basename(r'c:\pagefile.sys'), 'pagefile')

	'''
	fullpath = path_get(fullpath)
	fname = os.path.basename(fullpath)
	return os.path.splitext(fname)[0]

def file_name_add(fullpath, suffix:str='', prefix:str='')->str:
	''' Adds suffix or prefix to a file name.
		Example:

			file_name_add('my_file.txt', suffix='_1')
			> 'my_file_1.txt'
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

		tass( file_name_rem('my_file_1.txt', suffix='_1'), 'my_file.txt')
		tass( file_name_rem('my_file_1.txt', suffix='_'), 'my_file_1.txt')
		tass( file_name_rem('tmp_foo.txt', prefix='tmp_'), 'foo.txt')
	
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

def dir_dirs(fullpath, subdirs:bool=True)->Iterator[str]:
	r'''
	Returns list of full paths of all directories
	in this directory and its subdirectories.

		tass( r'c:\windows\System32' in dir_dirs(r'c:\windows', False), True )

	'''
	fullpath = path_get(fullpath)

	for dirpath, dirs, _ in os.walk(fullpath, topdown=True):
		for d in dirs: yield os.path.join(dirpath, d)
		if not subdirs: return

def dir_files(fullpath, subdirs:bool=True
, **rules)->Iterator[str]:
	r'''
	Returns list of full filenames of all files
	in the given directory and its subdirectories.  
	*subdirs* - including files from subfolders.  
	*rules* - rules for the `path_rule` function  

		tass( tuple(dir_files('plugins', in_ext='jpg') ), tuple() )
		tass(
			tuple(dir_files('plugins', in_ext='py'))[0]
			, 'plugins\\constants.py'
		)
		tass(
			tuple( dir_files('plugins', ex_ext='pyc') )
			, tuple( dir_files('plugins', in_ext='py') )
		)
		tass(
			tuple( dir_files('plugins', ex_path='plugins\\') )
			, tuple()
		)

	'''
	fullpath = path_get(fullpath)
	if rules: in_rules, ex_rules = path_rule(**rules)
	for dirpath, dirs, filenames in os.walk(fullpath, topdown=True):
		if not subdirs: dirs.clear()
		for fname in filenames:
			if rules:
				fpath = dirpath + '\\' + fname
				if _path_match(
					path=fpath
					, in_rules=in_rules
					, ex_rules=ex_rules
				):
					yield fpath
			else:
				 yield dirpath + '\\' + fname

def dir_rnd_files(fullpath, file_num:int=1
, attempts:int=5, **rules)->Iterator[str]:
	'''
	Gets random files from a directory or None
	if nothing is found.  
	*file_num* - how many files to return.  
	*rules* - a tuple of rules from the `path_rule`.

	Designed for large directories that take a significant
	amount of time to list.  
	Example:

		dir_rnd_files('.')
		tuple(dir_rnd_files('.', ex_ext='py'))
	
	Compared to `dir_files` with `random.choice`:

		> benchmark(lambda: random.choice( list(dir_files(temp_dir() ) ) ), b_iter=10)
		benchmark: 113 367 113 ns/loop

		> benchmark(dir_rnd_files, a=(temp_dir(), ), b_iter=10)
		620

		> len( tuple( dir_files( temp_dir() ) ) )
		1914
		
	'''
	fullpath = path_get(fullpath)
	found_num = 0
	in_rules, ex_rules = path_rule(**rules)
	for _ in range(file_num):
		for _ in range(attempts):
			path = fullpath
			if found_num == file_num: return
			for _ in range(attempts):
				dlist = os.listdir(path)
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
					):
						found_num += 1
						yield path
						break
					else:
						break

def dir_rnd_dir(fullpath, attempts:int=5
, filter_func=None)->str:
	'''
	Same as `dir_rnd_file` but returns a directory.
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

def dir_purge(fullpath, days:int=0, subdirs:bool=False
, creation:bool=False, test:bool=False
, print_del:bool=False, **rules)->int:
	r'''
	Deletes files older than *x* days.
	Returns number of deleted files and folders. 
	
	*days=0* - delete everything  
	*creation* - use date of creation, otherwise use last
	modification date.  
	*subdirs* - delete in subfolders too. Empty subfolders 
	will be deleted.  
	*test* - only print files and folders that should be removed.  
	*print_del* - print path when deleting.  
	*rules* - rules for the `path_rule` function  
	'''
	def print_d(fn:str, reason:str):
		if print_del: print('dir_purge:', reason, os.path.relpath(fn, fullpath))

	def robust_remove_file(fn):
		nonlocal counter
		try:
			print_d(fn, 'file')
			file_delete(fn)
			counter += 1
		except:
			pass
		
	def robust_remove_dir(fn):
		nonlocal counter
		try:
			print_d(fn, 'dir')
			shutil.rmtree(fn)
			counter += 1
		except:
			pass
		
	def fn_print(fn):
		nonlocal counter
		counter += 1
		print(os.path.relpath(fn, fullpath))

	fullpath = path_get(fullpath)
	counter = 0
	dirs, files = (), ()
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
		if not any( len(t[2]) for t in os.walk(fpath) ):
			dir_func(fpath)
	return counter

def file_name(fullpath)->str:
	''' Returns only file name from fullpath '''
	return os.path.basename( path_get(fullpath) )

def file_name_wo_ext(fullpath)->str:
	return os.path.splitext(path_get(fullpath))[0]

def file_dir(fullpath)->str:
	''' Returns directory from fullpath
	'''
	return os.path.dirname(path_get(fullpath))

def file_dir_repl(fullpath, new_dir:str)->str:
	''' Changes the directory of the file (in full path)
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

def drive_free(letter:str, unit:str='GB')->int:
	''' Returns drive free space in GB, MB, KB or B
	'''
	e = _SIZE_UNITS.get(unit.lower(), 1073741824)
	try:
		return shutil.disk_usage(f'{letter}:\\')[2] // e
	except:
		return -1

def dir_list(fullpath, **rules)->Iterator[str]:
	r'''
	Returns all directory content (dirs and files).  
	*rules* - rules for the `path_rule` function.  

		tass( 'resources\\icon.png' in dir_list('resources'), True)
		tass( 'resources\\icon.png' in dir_list('resources', ex_ext='png'), False)
		tass(
			benchmark(lambda d: tuple(dir_list(d)), 'log', b_iter=5)
			, 500_000
			, '<'
		)

	'''
	fullpath = path_get(fullpath)
	if rules: in_rules, ex_rules = path_rule(**rules)
	for dirpath, dirnames, filenames in os.walk(fullpath):
		for d in dirnames:
			fpath = dirpath + '\\' + d
			if rules:
				if _path_match(
					path=fpath
					, in_rules=in_rules
					, ex_rules=ex_rules
				):
					yield fpath
			else:
				yield fpath
		for f in filenames:
			fpath = dirpath + '\\' + f
			if rules:
				if _path_match(
					path=fpath
					, in_rules=in_rules
					, ex_rules=ex_rules
				):
					yield fpath
			else:
				yield fpath

def dir_find(fullpath, only_files:bool=False)->list:
	'''
	Returns list of paths in specified folder.  
	*fullpath* passed to **glob.glob**  
	*only_files* - return only files and not
	files and directories  

	Examples:
		dir_list('d:\\folder\\*.jpg')
		dir_list('d:\\folder\\**\\*.jpg')

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
	'''
	Returns directory size without symlinks.  
	*skip_err* - do not raise an exeption on non-existent files.
	'''
	fullpath = path_get(fullpath)
	udiv = _SIZE_UNITS.get(unit.lower(), 1)
	total_size = 0
	for dirpath, _, filenames in os.walk(fullpath):
		for fn in filenames:
			fpath = os.path.join(dirpath, fn)
			if os.path.islink(fpath): continue
			try:
				total_size += os.path.getsize(fpath)
			except Exception as e:
				if skip_err:
					tdebug(f'skip {fpath} ({e})')
					continue
				else:
					raise e
	return total_size // udiv

def dir_zip(fullpath, destination=None
, do_cwd:bool=False)->str:
	''' Compresses folder and returns the full
		path to archive.
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
		new_fullpath = _dir_slash(destination) \
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

def file_zip(fullpath, destination=None)->str:
	''' Compresses a file or files to archive.
		fullpath - string with fullpath or list with fullpaths.
		destination - full path to the archive or destination
		directory.
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

def temp_dir(new_dir:str=None)->str:
	''' Returns full path of temp dir (without trailing slash).
		If new_dir - creates folder in temp dir
		and returns its full path.
	'''
	if not new_dir:
		return tempfile.gettempdir()
	if new_dir == 'temp':
		new_dir = os.path.join(
			tempfile.gettempdir()
			, time.strftime("%m%d%H%M%S") + random_str(5)
		)
	else:
		new_dir = os.path.join(tempfile.gettempdir(), new_dir)
	try:
		os.mkdir(new_dir)
	except FileExistsError: pass
	return new_dir

def temp_file(prefix:str='', suffix:str=''
, content=None, encoding='utf-8')->str:
	'''
	Returns the full name for the temporary file.  
	If *content* is specified then writes content to the file.
	'''
	fname = os.path.join(tempfile.gettempdir()
		, prefix + time.strftime('%m%d%H%M%S') + random_str(5) + suffix)
	if content: file_write(fname, content=content, encoding=encoding)
	return fname

def file_hash(fullpath, algorithm:str='crc32'
, buf_size:int=65536)->str:
	''' Returns hash of file.
		algorithm - 'crc32' or any algorithm
		from hashlib (md5, sha512 etc).
	'''
	fullpath = path_get(fullpath)
	algorithm = algorithm.lower().replace('-', '')
	if algorithm == 'crc32':
		prev = 0
		for eachLine in open(fullpath, 'rb'):
			prev = crc32(eachLine, prev)
		return '%X' % (prev & 0xFFFFFFFF)		
	else:
		hash_obj = getattr(hashlib, algorithm)()
		with open(fullpath, 'rb') as fi:
			for chunk in iter(lambda: fi.read(buf_size), b''):
				hash_obj.update(chunk)
		return hash_obj.hexdigest()
	
def drive_list(exclude:str='')->str:
	'''
	Returns a string of local drive letters in lower case.
	Exclude - drives to exclude.
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

def shortcut_create(fullpath, dest:str=None, descr:str=None
, icon_fullpath:str=None, icon_index:int=None
, win_style:int=win32con.SW_SHOWNORMAL, cwd:str=None
, hotkey:int=None)->str:
	''' Creates shortcut to the file.
		Returns full path of shortcut.

		dest - shortcut destination. If None then
			use desktop path of current user.
		descr - shortcut description.
		icon_fullpath - source file for icon.
		icon_index - if specified and icon_fullpath is None
			then fullpath is used as icon_fullpath.
	'''
	fullpath = path_get(fullpath)
	if not descr: descr = file_name(fullpath)
	if not dest:
		dest = os.path.join(
			dir_user_desktop()
			, file_name(fullpath)
		)
	elif dir_exists(dest):
		dest = os.path.join(dest, file_name(fullpath) )
	if not dest.endswith('lnk'): dest = file_ext_replace(dest, 'lnk')
	if icon_index != None and not icon_fullpath:
		icon_fullpath = fullpath
	if icon_fullpath and icon_index == None: icon_index = 0
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
	if icon_index != None: shortcut.SetIconLocation(fullpath, 0)
	persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
	persist_file.Save(dest, 0)
	pythoncom.CoUninitialize()
	return dest

def file_print(fullpath, printer:str=None
, use_alternative:bool=False)->bool:
	''' Prints file on specified printer.
		Non-blocking.
		Returns True on success.
		If no printer is specified - print on 
		system default printer.
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
		self.use_save_to = use_save_to
		if not mime_type:
			mime_type = mimetypes.MimeTypes() \
				.guess_type(self.fullpath)[0]
			if not mime_type: mime_type = tcon.MIME_HTML
		self.mime_type = mime_type
		if not name: name = file_name(fullpath)
		self.name = name
def file_lock_wait(fullpath, wait_interval:str='100 ms'
, log:bool=False)->bool:
	'''
	Blocks execution until the file is available.
	Usage - wait for another process to stop writing to the file.
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
				dev_print('File is locked:', file_name(fullpath))
			time_sleep(wait_interval)
		except Exception as e:
			tprint('wrong exception:', file_name(fullpath), repr(e))
			return False

def file_relpath(fullpath, start)->str:
	r'''
	Returns a relative path.  

		tass(
			file_relpath(r'c:\Windows\System32\calc.exe', r'c:\Windows')
			, 'System32\\calc.exe'
		)

	'''
	fullpath = path_get(fullpath)
	start = path_get(start)
	return os.path.relpath(fullpath, start=start)

def _file_name_pe(filename:str):
	for char, repl in _FORBIDDEN_DICT.items():
		filename = filename.replace(char, repl)
	return filename

def var_fpath(var)->str:
	if is_iter(var):
		return os.path.join(_VAR_DIR
		, *map(_file_name_pe, var) )
	else:
		return os.path.join(_VAR_DIR, _file_name_pe(var) )

def var_open(var:str)->None:
	' Opens variable in default editor '
	win32api.ShellExecute(None, 'open', var_fpath(var)
	, None, None, 0)


def var_get(var:str, default=None, encoding:str='utf-8'
, as_literal:bool=False):
	'''
	Gets the *disk variable*.  
	*as_literal* - converts to a literal (dict, list, tuple etc).
	Dangerous! - it's just `eval`, not `ast.literal_eval`

		var_set('_test', 1)
		tass( var_get('_test'), '1')
		tass( var_get('_test', as_literal=True), 1 )
		tass( var_del('_test'), True)

	'''
	fpath = var_fpath(var)
	try:
		content = file_read(fpath, encoding=encoding)
	except FileNotFoundError:
		return default
	if as_literal:
		return eval(content) if content != '' else ''
	else:
		return content

def var_set(var, value, encoding:str='utf-8'):
	'''
	Sets the disk variable.

		var_set('_test', 5)
		tass( var_get('_test'), '5')
		tass( var_del('_test'), True)
		var = ('file', 'c:\\pagefile.sys')
		var_set(var, 1)
		tass( var_get(var, 1), '1' )
		tass( var_del(var), True )

	'''
	fpath = var_fpath(var)
	value = str(value)
	try:
		file_write(fpath, value, encoding=encoding)
	except FileNotFoundError:
		os.makedirs(_VAR_DIR)
		file_write(fpath, value, encoding=encoding)

def var_del(var:str):
	'''
	Deletes variable. Returns True if var exists.

		var_set('_test', 'a')
		tass( var_del('_test'), True)
		
	'''
	fpath = var_fpath(var)
	try:
		os.remove(fpath)
		return True
	except FileNotFoundError:
		return False

def var_add(var:str, value, var_type=None
, encoding:str='utf-8'):
	'''
	Adds the value to the previous value and returns the new value.

		tass(var_add('_test', 5, var_type=int), 5)
		tass(var_add('_test', 3),  8)
		tass(var_del('_test'), True)

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

def var_lst_get(var:str, default=[]
, encoding:str='utf-8', com_str:str='#')->list:
	'''
	Returns list with the text lines. Excludes empty lines
	and lines that begin with *com_str*

		var_lst_set('_test', ['a', 'b'])
		tass(var_lst_get('_test'), ['a', 'b'])
		var_lst_set('_test', map(str, (1, 2)))
		tass(var_lst_get('_test'), ['1', '2'])
		tass(var_del('_test'), True)

	'''
	cont = var_get(var, default=default
	, encoding=encoding)
	if cont:
		lst = cont.strip().splitlines()
		return [l for l in lst
			if l and (not l.startswith(com_str)) ]
	else:
		return cont

def var_mod(var)->datetime.datetime:
	'''
	Returns the date of the last modification.
	'''
	fpath = var_fpath(var)
	return file_date_m(fpath)

def var_mod_dif(var, unit:str='sec')->int:
	'''
	Returns how many time units have passed
	since the last change.

		tass(var_mod_dif('_public_suffix_list', 'month'), 2, '<')

	'''
	return time_diff(var_mod(var), unit=unit)

def var_lst_set(var, value, encoding:str='utf-8'):
	'''
	Sets the disk list variable.
		var_lst_set('_test', ['a', 'b', 1])
		tass( var_lst_get('_test'), ['a', 'b', '1'])
		tass( var_del('_test'), True)

	'''
	var_set(var, '\n'.join(map(str, value))
	, encoding=encoding)

def var_lst_add(var, value, encoding:str='utf-8')->list:
	'''
	Adds the value to the list
	and returns the list.

		var_lst_set('_test', 'ab')
		tass( var_lst_add('_test', 'c'), ['a', 'b', 'c'] )
		tass( var_del('_test'), True)

	'''
	lst = var_lst_get(var, encoding=encoding)
	lst.append(str(value))
	var_lst_set(var, lst, encoding=encoding)
	return lst

def var_lst_ext(var, value, encoding:str='utf-8')->list:
	'''
	Expands the list with the values of *value*. Returns
	new list.

		var_lst_set('_test_ext', 'ab')
		tass( var_lst_ext('_test_ext', 'cd'), ['a', 'b', 'c', 'd'] )
		tass( var_del('_test_ext'), True)

	'''
	lst = var_lst_get(var, encoding=encoding)
	lst.extend(map(str, value))
	var_lst_set(var, lst, encoding=encoding)
	return lst

def file_drive(fullpath)->str:
	'''
	Returns a drive letter in lowercase from a file name:

		tass( file_drive(r'c:\\pagefile.sys'), 'c' )

	'''
	fullpath = path_get(fullpath)
	return os.path.splitdrive(fullpath)[0][:1].lower()

def file_conf_read(fullpath:str, encoding:str='utf-8'
, lowercase:bool=True, as_literal:bool=True)->dict:
	'''
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
def drive_io(drive_num:int=None)->Iterator[namedtuple]:
	'''
	Returns physical drive (not partition!) I/O generator
	that returns a named tuples with counters. Example:

		dio = drive_io()
		print(next(dio)[0].read_bytes)
		time_sleep('1 sec')
		print(
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
			if (drive_num != None) and drive_num != drive: continue
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
		if drive_num:
			yield cur[drive_num]
		else:
			yield cur

def path_rule(
	ex_ext:Iterable = ()
	, in_ext:Iterable = ()
	, ex_path:Iterable = ()
	, in_path:Iterable = ()
	, ex_dir:Iterable = ()
	, in_dir:Iterable = ()
	, ex_name:Iterable = ()
	, in_name:Iterable = ()
	, in_datem_aft:datetime.datetime = None
	, ex_datem_aft:datetime.datetime = None
	, in_datem_bef:datetime.datetime = None
	, ex_datem_bef:datetime.datetime = None
	, in_datec_aft:datetime.datetime = None
	, ex_datec_aft:datetime.datetime = None
	, in_datec_bef:datetime.datetime = None
	, ex_datec_bef:datetime.datetime = None
	, in_datea_aft:datetime.datetime = None
	, ex_datea_aft:datetime.datetime = None
	, in_datea_bef:datetime.datetime = None
	, ex_datea_bef:datetime.datetime = None
)->Tuple[ List[Callable], List[Callable] ]:
	r'''
	Creates a list of rules (functions) to check
	a file or directory.  
	*in_\** - rule to include, *ex_\** - rule to exclude.  
	All rules are case-insensitive. All rules may be a string
	or a tuple/list of strings:  
	*ex_ext='py'*  
	*ex_ext=('py', 'pyc')*  

	*ex_ext*, *in_ext* - by extension.  
	*ex_path*, *in_path* - by any part of a full file path  
	*in_name*, *ex_name* - by part of file name.  
	*ex_dir*, *in_dir* - by beginning of a file path  

	File date variables.  
	Date value is a `datetime.datetime` or `datetime.timedelta`
	or a string based on `tcon.DATE_STR_HUMAN` pattern
	like that: '2023.02.12 0:0:0'  
	*datem*, *datea*, *datec* - date of modification, access, creation.  
	*in_datem_aft* - by date of modification (greater or equal)  
	*ex_datem_aft* - by date of modification (greater or equal)  

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
		tdebug(time_att, ('<=' if is_bef else '>=')
		, f'{tstamp} ({val})')
		if is_bef:
			lst.append(
				lambda p, a=time_att, t=tstamp: getattr(os.stat(p), a) <= t
			)
		else:
			lst.append(
				lambda p, a=time_att, t=tstamp: getattr(os.stat(p), a) >= t
			)
	return in_rules, ex_rules

def _path_match(path:str, in_rules:list, ex_rules:list)->bool:
	'''
	Returns True if path matches rules from the `path_rule`.

		from plugins.plugin_filesystem import _path_match
		inr, exr = path_rule(in_ext='py', ex_ext='pyc')
		tass( _path_match(r'crontab.py', inr, exr), True )
		tass( _path_match(r'crontab.pyc', inr, exr), False )
		inr, exr = path_rule(ex_path='.pyc')
		tass( _path_match(r'crontab.pyc', inr, exr), False )
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
		files = tuple(dir_files('plugins'))
		tass( tuple( pf(files, ex_dir='__pycache__'))[0], 'plugins\\constants.py')
		tass( tuple( pf(files, ex_ext='pyc'))[0], 'plugins\\constants.py')
		tass( tuple( pf(files, ex_ext='pyc', ex_path='_TOOLS_patc'))[-1], 'plugins\\tools.py')
		tass( tuple( pf(files, ex_ext=('pyc', 'py') ) ), ())
		tass( tuple( pf(files, in_ext='txt' ) ), ())
		tass( tuple( pf(files, in_ext='py', ex_path='_TOOLS_patc'))[-1], 'plugins\\tools.py')
		tass( tuple( pf(files, in_path='constants.py'))[0], 'plugins\\constants.py')
		tass( tuple( pf(files, in_dir='\\plugins\\', ex_ext='pyc', ex_path='paTch'))[-1], 'plugins\\tools.py')
		tass( tuple( pf(files, in_name='crypt') )[0], 'plugins\plugin_crypt.py')
		tass( tuple( pf(files, in_ext='py', ex_name=('plug', 'const')) )[0], r'plugins\tools.py')
		tass(
			tuple( pf(files, in_datem_aft=datetime.datetime(2024, 1, 1), ) )
			, ()
		)
		tass(
			tuple( pf(files, ex_datem_aft=datetime.datetime(2020, 12, 24), ) )
			, ()
		)
		tass(
			tuple( pf(files, in_datem_aft='2024.1.1 0:0:0', ) )
			, ()
		)
		tass(
			tuple( pf(files, ex_datem_aft='2020.12.24 0:0:0', ) )
			, ()
		)
		tass(
			tuple( pf(files, in_ext='py', in_datem_bef='2020.12.24 0:0:0', ) )
			, ()
		)

	'''
	in_rules, ex_rules = path_rule(**rules)
	for path in paths:
		if _path_match(path=path, in_rules=in_rules, ex_rules=ex_rules):
			yield path


class DirSync:
	'''
	Syncrhonize two directories.
	'''
	

	def __init__(
		self
		, src_dir:str
		, dst_dir:str
		, report:bool=False
		, max_table_width:int=100
		, **rules
	):
		'''
		*report* - print every file copy/del operation.
		'''
		self._src_dir = path_get(src_dir)
		self._dst_dir = path_get(dst_dir)
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
		self.duration = ''
	
	def _walk(self):
		' Reads contens of src and dst directories '
		tstart = time_now()
		self._src_files = set()
		self._src_dirs = set()
		self._dst_files = set()
		self._dst_dirs = set()
		for dirpath, dirnames, filenames in os.walk(self._src_dir):
			for d in dirnames:
				self._src_dirs.add(
					os.path.join(dirpath, d)
				)
			for f in filenames:
				self._src_files.add(
					os.path.join(dirpath, f)
				)
		for dirpath, dirnames, filenames in os.walk(self._dst_dir):
			for d in dirnames:
				self._dst_dirs.add(
					os.path.join(dirpath, d)
				)
			for f in filenames:
				self._dst_files.add(
					os.path.join(dirpath, f)
				)
		tdebug(time_diff_str(tstart))


	def compare(self)->bool:
		'''
		Reads the directories and makes a comparison.
		'''
		tstart = time_now()
		self.errors = dict()
		self._walk()
		slen = len(self._src_dir.rstrip('\\')) + 1
		dlen = len(self._dst_dir.rstrip('\\')) + 1
		self._src_files = set( (p[slen:].lower() for p in self._src_files) )
		self._dst_files = set( (p[dlen:].lower() for p in self._dst_files) )
		if self._rules:
			self._src_files = set(path_filter(
				paths=self._src_files
				, **self._rules
			))
		self._src_only_files = self._src_files - self._dst_files
		self._dst_only_files = self._dst_files - self._src_files
		self._src_dirs = set( (p[slen:].lower() for p in self._src_dirs) )
		self._dst_dirs = set( (p[dlen:].lower() for p in self._dst_dirs) )
		if self._rules:
			self._src_dirs = set(path_filter(
				paths=self._src_dirs
				, **self._rules
			))
		self._dst_only_dirs = self._dst_dirs - self._src_dirs
		self._get_new_files()
		self.duration = time_diff_str(tstart, no_ms=True)
		tdebug('done in', self.duration)
		return len(self.errors) == 0
	
	def _log(self, oper:str, path:str):
		' Print current file operation '
		if not self._report: return
		maxw = self._max_table_width - len(oper) - 7
		print(f'sync {oper}: {path_short(path, maxw)}')
	
	def _get_new_files(self):
		self._new_files = set()
		for rpath in (self._src_files.intersection(self._dst_files)):
			try:
				src_mtime = int(os.path.getmtime(
					'\\\\?\\' + os.path.join(self._src_dir, rpath)
				))
				dst_mtime = int(os.path.getmtime(
					'\\\\?\\' + os.path.join(self._dst_dir, rpath)
				))
				if src_mtime > dst_mtime:
					self._new_files.add(rpath)
			except:
				tdebug('mdate error', exc_text())
				self.errors[rpath] = 'mdate error'

	def _copy(self):
		''' Copy unique and new files from src to dst '''
		for fileset in self._src_only_files, self._new_files:
			for rpath in fileset:
				try:
					self._log('copy', rpath)
					file_copy(
						fullpath=(self._src_dir, rpath)
						, destination=(self._dst_dir, rpath)
					)
				except:
					tdebug('copy error', exc_text())
					self.errors[rpath] = 'copy error'
	
	def _delete_dirs(self):
		'''
		Deletes dst-only directories and removes
		their files from self._dst_only_files.
		'''
		errors = set()
		for rpath in self._dst_only_dirs:
			try:
				shutil.rmtree( os.path.join(self._dst_dir, rpath) )
				self._log('del dir', rpath)
			except:
				errors.add(rpath)
				tdebug('dir del error', exc_text())
				self.errors[rpath] = 'dir del error'
		del_dirs = self._dst_only_dirs - errors
		self._dst_only_files = set(
			f for f in self._dst_only_files
			if not any(f.startswith(d) for d in del_dirs)
		)

	def _delete_files(self):
		' Delete files that do not exist in the src '
		for rpath in self._dst_only_files:
			try:
				file_delete((self._dst_dir, rpath))
				self._log('del file', rpath)
			except FileNotFoundError:
				pass
			except:
				tdebug('file del error', exc_text())
				self.errors[rpath] = 'file del error'

	def print_diff(self):
		'''
		Print a table with the difference between
		the directories.
		'''
		print('\nDirSync:', self._src_dir, '->', self._dst_dir)
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
		print(
			f'Done in {self.duration}'
			, f'src files: {len(self._src_files)}'
			, f'src only files: {len(self._src_only_files)}'
			, f'dst only files: {len(self._dst_only_files)}'
			, f'dst only dirs: {len(self._dst_only_dirs)}'
			, f'new files: {len(self._new_files)}'
			, f'errors: {len(self.errors)}'
			,''
			, sep='\n'
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
		tstart = time_now()
		self.errors = dict()
		self._copy()
		self._delete_dirs()
		self._delete_files()
		self.duration = time_diff_str(tstart, no_ms=True)
		tdebug('done in', self.duration)
		return len(self.errors) == 0


def dir_sync(src_dir, dst_dir, report:bool=False
, **rules)->dict:
	'''
	Syncrhonize two directories.  
	For *rules* see the `path_rule`.  
	Returns dict with errors:  
	
		{'path\\file.exe': 'copy error', ...}

	'''
	sync = DirSync(src_dir=src_dir, dst_dir=dst_dir
	, **rules)
	sync.compare()
	sync.sync()
	if report: sync.print_diff()
	if sync.errors and report: sync.print_errors()
	return sync.errors

def path_short(fullpath, max_len:int=100)->str:
	r'''
	Shortens a long file name to display.

		path = r'c:\Windows\System32\msiexec.exe'
		tass(path_short(path, 22), 'c:\Windo...msiexec.exe')
		tass(path_short(path, 23), 'c:\Window...msiexec.exe')

	'''
	if len(fp := fullpath) <= max_len: return fullpath
	return fp[:( -(-max_len // 2 ) )-3] + '...' + fp[-(max_len//2):]



class DirDup:
	r'''
	First we find groups of files with the same size
	, then we look for unique ones within those groups.
	'''
	ALGO_SIZE = 'Size'
	ALGO_MDATE = 'Modification date'
	ALGO_CDATE = 'Creation date'
	ALGO_HASH_BEG = 'Hash of the beginning'
	ALGO_HASH_FULL = 'Hash of the whole'

	def __init__(self, src_dir:Union[str, tuple, list], algo:str
	, hash_size_limit_perc:int=5, **rules)->None:
		assert algo in (self.ALGO_SIZE, self.ALGO_HASH_BEG
		, self.ALGO_HASH_FULL, self.ALGO_MDATE, self.ALGO_CDATE), 'unknown algorithm'
		self._src_dirs:tuple = (src_dir,) if isinstance(src_dir, str) else src_dir
		self._algo:str = algo
		self._dtype = 'mdate' if self._algo == self.ALGO_MDATE else 'cdate'
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
		for d in self._src_dirs:
			for fpath in dir_files(d, **self._rules):
				self._files[fpath] = {'unique': True}
				att = win32file.GetFileAttributesEx(fpath)
				self._files[fpath]['size'] = att[4]
				self._files[fpath]['mdate'] = att[3]
				self._files[fpath]['cdate'] = att[1]

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
					self._files[fpath]['unique'] = False
			self._dups = tuple(f for f,p in self._files.items() if not p['unique'])
			tdebug(f'done in {time_diff_str(tstart)}')
			return
		for size, fpaths in self._sizes.items():
			if len(fpaths) == 1: continue
			if self._algo in (self.ALGO_MDATE, self.ALGO_CDATE):
				dates = tuple(self._files[f][self._dtype].timestamp() for f in fpaths)
				for fpath in fpaths:
					self._files[fpath]['unique'] = dates.count(
						self._files[fpath][self._dtype].timestamp()
					) == 1
			else:
				hashes = list()
				for fpath in fpaths:
					hsh = self._file_md5(fpath, fsize=size)
					self._files[fpath]['hash'] = hsh
					hashes.append(hsh)
				for fpath in fpaths:
					self._files[fpath]['unique'] = hashes.count(
						self._files[fpath]['hash']
					) == 1
		self._dups = tuple(f for f,p in self._files.items() if not p['unique'])
		tdebug(f'done in {time_diff_str(tstart)}')
	
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
			table.append((name, str(props['unique']), sign))
		table_print(table, max_table_width=(100, 0), trim_func=path_short
		, sorting=(1, 0))

	def print_dup(self, fullname:bool=False):
		' Print duplicates only '
		table = [('File', self._algo)]
		for size, fpaths in self._sizes.items():
			if len(fpaths) == 1: continue
			for fpath in fpaths:
				name = fpath if fullname else file_name(fpath)
				props = self._files[fpath]
				if props['unique']: continue
				if self._algo == self.ALGO_SIZE:
					sign = size
				elif self._algo in (self.ALGO_MDATE, self.ALGO_CDATE):
					sign = props[self._dtype].strftime(tcon.DATE_STR_HUMAN)
				else:
					sign = props['hash']
				table.append((name, sign))
		table_print(table, max_table_width=(100, 0), trim_func=path_short
		, sorting=(1, 0))


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

if __name__ != '__main__': patch_import()