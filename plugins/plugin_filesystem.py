import os
import sys
import stat
import time
import glob
from contextlib import contextmanager
import csv
import pyodbc
import zipfile
from distutils import dir_util
from zlib import crc32
import tempfile
import datetime
import win32con
import win32com
import win32print
import hashlib
import pythoncom

import win32api
from win32com.shell import shell, shellcon
from pathlib import Path
import shutil
from .tools import random_str, tdebug


_SIZE_UNITS = {'gb':1073741824, 'mb':1048576, 'kb':1024, 'b':1}

def _dir_slash(dirpath:str)->str:
	''' Adds a trailing slash if it's not there. '''
	if dirpath.endswith('\\'): return dirpath
	return dirpath + '\\'

def _fix_fullpath(fullpath):
	''' Join list of paths and optionally
		fix long path.
	'''
	if isinstance(fullpath, (list, tuple)):
		fullpath = os.path.join(*map(str, fullpath))
	if (
		len(fullpath) > 255
		and not '\\\\?\\' in fullpath
		and fullpath[1:3] == ':\\'
	):
		return '\\\\?\\' + fullpath
	return fullpath

def file_read(fullpath, encoding:str='utf-8')->str:
	''' Returns content of file '''
	fullpath = _fix_fullpath(fullpath)
	if encoding == 'binary':
		with open(fullpath, 'rb') as f:
			return f.read()
	else:
		with open(fullpath, 'tr', encoding=encoding) as f:
			return f.read()

def file_write(fullpath, content:str
, encoding:str='utf-8')->str:
	''' Saves content to a file.
		Creates file if the fullpath doesn't exist.
		If fullpath is '' or None - uses temp_file().
		Returns fullpath.
	'''
	if encoding == 'binary':
		open_args = {'mode': 'wb+'}
	else:
		open_args = {'mode': 'wt+', 'encoding': encoding
		, 'errors': 'ignore'}
	if fullpath:
		fullpath = _fix_fullpath(fullpath)
		if not os.path.exists(os.path.dirname(fullpath)):
			os.makedirs(os.path.dirname(fullpath))
	else:
		fullpath = temp_file()
	with open(fullpath, **open_args) as f:
		f.write(content)
	return fullpath

def file_ext_replace(fullpath, new_ext:str)->str:
	' Replaces file extension '
	return os.path.splitext(_fix_fullpath(fullpath))[0] + '.' + new_ext

def file_rename(fullpath, dest:str
, overwrite:bool=False)->str:
	''' Renames path.
		dest - fullpath or just new file name
		without parent directory.
		overwrite - overwrite destination file
		if exists.
		Returns destination.
	'''
	fullpath = _fix_fullpath(fullpath)
	if not ':' in dest:
		dest = os.path.join(os.path.dirname(fullpath), dest)
	try:
		os.rename(fullpath, dest)
	except FileExistsError as e:
		if overwrite:
			file_delete(dest)
			os.rename(fullpath, dest)
		else:
			raise e
	return dest

dir_rename = file_rename

def file_log(fullpath, message:str, encoding:str='utf-8'
, time_format:str='%Y.%m.%d %H:%M:%S'):
	''' Writes message to log '''
	fullpath = _fix_fullpath(fullpath)
	with open(fullpath, 'at+', encoding=encoding) as f:
		f.write(time.strftime(time_format) + '\t' + message + '\n')

def file_copy(fullpath, destination:str
, copy_metadata:bool=False):
	''' Copies file to destination.
		Destination may be fullpath or folder name.
		If destination file exists it will be overwritten.
		If destination is a folder, subfolders will
		be created if they don't exist.
	'''
	fullpath = _fix_fullpath(fullpath)
	func = shutil.copy2 if copy_metadata else shutil.copy
	try:
		return func(fullpath, destination)
	except FileNotFoundError:
		try:
			os.makedirs(
				os.path.dirname(destination)
			)
			return func(fullpath, destination)
		except FileExistsError: pass

def file_append(fullpath, content:str)->str:
	''' Append content to a file. Creates fullpath
		if not specified.
		Returns fullpath.
	'''
	if fullpath:
		fullpath = _fix_fullpath(fullpath)
	else:
		fullpath = temp_file()
	with open(fullpath, 'a+') as fd:
		fd.write(content)
	return fullpath

def file_move(fullpath, destination:str):
	''' Move file to destination.
		Destination may be fullpath or folder name.
		If destination path exist it will be overwritten.
	'''
	fullpath = _fix_fullpath(fullpath)
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
	fullpath = _fix_fullpath(fullpath)
	try:
		os.remove(fullpath)
	except PermissionError:
		try:
			os.chmod(fullpath, stat.S_IWRITE)
			os.remove(fullpath)
		except Exception as e:
			print(f'file_delete error: {e}')
	except FileNotFoundError:
		pass

def file_recycle(fullpath, silent:bool=True)->bool:
	''' Move file to the recycle bin
		silent - do not show standard windows
		dialog to confirm deletion.
		Returns True on successful operation.
	'''
	fullpath = _fix_fullpath(fullpath)
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
	fullpath = _fix_fullpath(fullpath)
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
	fullpath = _fix_fullpath(fullpath)
	if not fullpath: return temp_dir('temp')
	fullpath = fullpath.rstrip('.').rstrip(' ')
	try:
		os.makedirs(fullpath)
	except FileExistsError: pass
	return fullpath

def dir_delete(fullpath):
	''' Deletes folder with it's contents '''
	fullpath = _fix_fullpath(fullpath)
	try:
		shutil.rmtree(fullpath
		, onerror=lambda func, path, exc: file_delete(path))
	except FileNotFoundError:
		pass

def dir_exists(fullpath)->bool:
	return os.path.isdir( _fix_fullpath(fullpath) )

def file_exists(fullpath)->bool:
	return os.path.isfile( _fix_fullpath(fullpath) )

def path_exists(fullpath)->bool:
	''' Check if directory or file exist '''
	fullpath = _fix_fullpath(fullpath)
	p = Path(fullpath)
	return p.exists()

def file_size(fullpath, unit:str='b')->int:
	fullpath = _fix_fullpath(fullpath)
	e = _SIZE_UNITS.get(unit.lower(), 1)
	return os.stat(fullpath).st_size // e

def file_ext(fullpath)->str:
	''' Returns file extension in lower case
		without dot.
	'''
	fullpath = _fix_fullpath(fullpath)
	ext = os.path.splitext(fullpath)[1].lower()
	if ext == '': return ext
	return ext[1:]

def file_basename(fullpath)->str:
	''' Returns basename: file name without 
		parent folder and extension.
	'''
	fullpath = _fix_fullpath(fullpath)
	fname = os.path.basename(fullpath)
	return os.path.splitext(fname)[0]

def file_name_add(fullpath, suffix:str='')->str:
	''' Adds suffix to a file name before extension:
		file_name_add('my_file.txt', '_1') ->
		my_file_1.txt
		If suffix if not specified then add
		random string.
	'''
	fullpath = _fix_fullpath(fullpath)
	if suffix:
		suffix = str(suffix)
	else:
		suffix = '_' + random_str(5)
	name, ext = os.path.splitext(fullpath)
	return name + suffix + ext

def file_name_fix(filename:str, repl_char:str='_')->str:
	''' Replaces forbidden characters with repl_char.
		Don't use it with full path or it will replace
		all backslashes.
		Removes leading and trailing spaces and dots.
	'''

	new_fn = ''
	for char in filename.strip(' .'):
		if (char in '<>:"\\/|?*'
		or ord(char) < 32):
			new_fn += repl_char
		else:
			new_fn += char
	return new_fn

def dir_purge(fullpath, days:int=0, recursive:bool=False
, creation:bool=False, test:bool=False, rule=None):
	''' Deletes files older than x days.
		Returns number of deleted files and folders. 
		days=0 - delete everything
		creation - use date of creation, otherwise use last
			modification date.
		recursive - delete in subfolders too. Empty subfolders 
			will be deleted.
		test - only print files and folders that should be removed.
		rule - function that receivs file name and returns True
			if file should be deleted.
			Example: rule=lambda f: file_size(f) == 0
	'''
	
	def robust_remove_file(fullpath):
		nonlocal counter
		if rule:
			if not rule(fullpath): return
		try:
			file_delete(fullpath)
			counter += 1
		except:

			pass
		
	def robust_remove_dir(fullpath):
		nonlocal counter
		if rule:
			if not rule(fullpath): return
		try:
			shutil.rmtree(fullpath)
			counter += 1
		except:
			pass
		
	def file_print(fullpath):
		nonlocal counter
		counter += 1
		print(os.path.basename(fullpath))

	fullpath = _fix_fullpath(fullpath)
	counter = 0
	if days: delta = 24 * 3600 * days
	if creation:
		date_func = os.path.getctime
	else:
		date_func = os.path.getmtime
	if '*' in fullpath:
		pass
	elif fullpath.endswith('\\'):
		fullpath += '*'
	else:
		fullpath += '\\*'
	if recursive:
		fullpath = fullpath.replace('*', r'**\*')
	files = glob.glob(fullpath, recursive=recursive)
	current_time = time.time()
	if test:
		file_func = file_print
		dir_func = file_print
	else:
		file_func = robust_remove_file
		dir_func = robust_remove_dir
	for fi in files:
		if os.path.isdir(fi):
			folders = glob.glob(f'{fi}\\*')
			files_count = sum(
				[1 for sub in folders if not os.path.isdir(sub)]
			)
			if files_count == 0: dir_func(fi)
		else:
			if days:
				try:
					if (current_time - date_func(fi)) > delta:
						file_func(fi)
				except FileNotFoundError:
					pass
			else:
				file_func(fi)
	return counter

def file_name(fullpath)->str:
	''' Returns only name from fullpath
	'''
	return os.path.basename(_fix_fullpath(fullpath))

def file_name_wo_ext(fullpath)->str:
	return os.path.splitext(_fix_fullpath(fullpath))[0]

def file_dir(fullpath)->str:
	''' Returns directory from fullpath
	'''
	return os.path.dirname(_fix_fullpath(fullpath))

def file_backup(fullpath, dest_dir:str=''
, suffix_format:str='_%y-%m-%d_%H-%M-%S')->str:
	''' Copy somefile.txt to somefile_2019-05-19_21-23-02.txt
		dest_dir - destination. If not specified - current folder.
		Returns full path of new file.
	'''
	fullpath = _fix_fullpath(fullpath)
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

def dir_list(fullpath, only_files:bool=False)->list:
	''' Returns list of files in specified folder.
		'fullpath' passed to glob.glob

		only_files - return only files and not
		files and directories.

		Example:
			
			only files in folder:
				dir_list('d:\\folder\\*.jpg')

			with subfolders:
				dir_list('d:\\folder\\**\\*.jpg')
	'''
	fullpath = _fix_fullpath(fullpath)
	recursive = ('**' in fullpath)
	paths = glob.glob(fullpath, recursive=recursive)
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
	fullpath = _fix_fullpath(fullpath)
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
		Returns fullpath.
		content example:
		[
			{'name': 'some name',
			'number': 1}
			, {'name': 'another name',
			'number': 2}
			...	
		]
	'''
	fullpath = _fix_fullpath(fullpath)
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

def dir_size(fullpath, unit:str='b')->int:
	''' Returns directory size without symlinks '''
	fullpath = _fix_fullpath(fullpath)
	e = _SIZE_UNITS.get(unit.lower(), 1)
	total_size = 0
	for dirpath, _, filenames in os.walk(fullpath):
		for fi in filenames:
			fp = os.path.join(dirpath, fi)
			if not os.path.islink(fp):
				total_size += os.path.getsize(fp)
	return total_size // e

def dir_zip(fullpath, destination:str
, do_cwd:bool=False)->str:
	''' Compresses folder and returns the full
		path to archive.
		If destination is a folder then take
		archive name from fullpath directory name.
		Replaces destination if it exists.
		Returns destination.
	'''
	fullpath = _fix_fullpath(fullpath)
	EXT = 'zip'
	if os.path.isdir(destination):
		new_fullpath = _dir_slash(destination) \
			+ os.path.basename(fullpath)
		base_name = os.path.basename(fullpath)
		new_fullpath += '.zip'
	else:
		new_fullpath = destination
		base_name = os.path.basename(
			destination
		)
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
		shutil.move(result, new_fullpath)
	return new_fullpath

def file_zip(fullpath, destination:str)->str:
	''' Compresses a file or files to archive.
		fullpath - string with fullpath or list with fullpaths.
		destination - full path to the archive or destination
		directory.
	'''
	fullpath = _fix_fullpath(fullpath)
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
	elif isinstance(fullpath, list):
		with zipfile.ZipFile(
			destination, 'w'
		) as zipf:
			for fi in fullpath:
				zipf.write(fi, arcname=os.path.basename(fi)
					, compress_type=zipfile.ZIP_DEFLATED)
		return destination
	else:
		return Exception('file_zip: unknown type of fullpath')

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

def temp_file(suffix:str='')->str:
	''' Returns temporary file name. '''
	return os.path.join(tempfile.gettempdir()
		, time.strftime('%m%d%H%M%S') + random_str(5) + suffix)

def file_hash(fullpath, algorithm:str='crc32'
, buf_size:int=65536)->str:
	''' Returns hash of file.
		algorithm - 'crc32' or any algorithm
		from hashlib (md5, sha512 etc).
	'''
	fullpath = _fix_fullpath(fullpath)
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
	
def drive_list()->list:
	''' Returns a list of local drive letters '''
	drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
	return [d[0].lower() for d in drives]

@contextmanager
def working_directory(directory:str):
	''' Change current working directory
		and revert it back.
	'''
	owd = os.getcwd()
	try:
		os.chdir(directory)
		yield directory
	finally:
		os.chdir(owd)


def file_date_m(fullpath):
	' Returns file modification date in datetime '
	fullpath = _fix_fullpath(fullpath)
	ts = os.path.getmtime(fullpath)
	return datetime.datetime.fromtimestamp(ts)

def file_date_c(fullpath):
	' Returns file creation date in datetime '
	fullpath = _fix_fullpath(fullpath)
	ts = os.path.getctime(fullpath)
	return datetime.datetime.fromtimestamp(ts)

def file_date_a(fullpath):
	' Returns file access date in datetime '
	fullpath = _fix_fullpath(fullpath)
	ts = os.path.getatime(fullpath)
	return datetime.datetime.fromtimestamp(ts)

def file_attr_set(fullpath
, attribute:int=win32con.FILE_ATTRIBUTE_NORMAL):
	'''	Sets file attribute.
		Type 'win32con.FILE_' to get syntax hints for
		constants.
	'''
	win32api.SetFileAttributes(_fix_fullpath(fullpath), attribute)

def shortcut_create(fullpath, dest:str=None, descr:str=None
, icon_fullpath:str=None, icon_index:int=None
, win_style:int=win32con.SW_SHOWNORMAL, cwd:str=None):
	''' Creates shortcut to the file.
		Returns full path of shortcut.

		dest - shortcut destination. If None then
			use desktop path of current user.
		descr - shortcut description.
		icon_fullpath - source file for icon.
		icon_index - if specified and icon_fullpath is None
			then fullpath is used as icon_fullpath.
	'''
	fullpath = _fix_fullpath(fullpath)
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
		win32com.shell.shell.CLSID_ShellLink
		, None
		, pythoncom.CLSCTX_INPROC_SERVER
		, win32com.shell.shell.IID_IShellLink
	)
	shortcut.SetPath( os.path.abspath(fullpath) )
	shortcut.SetDescription(descr)
	shortcut.SetShowCmd(win_style)
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
	fullpath = _fix_fullpath(fullpath)
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
	return win32com.shell.shell.SHGetFolderPath(
		0, shellcon.CSIDL_DESKTOP, 0, 0)

def dir_user_startup()->str:
	' Returns full path to the startup directory of current user '
	return win32com.shell.shell.SHGetFolderPath(
		0, win32com.shell.shellcon.CSIDL_STARTUP, 0, 0)