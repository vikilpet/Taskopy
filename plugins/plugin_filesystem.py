import os
import stat
import time
import glob
import csv
import pyodbc
import zipfile
from distutils import dir_util
from zlib import crc32
import tempfile
import hashlib
from pathlib import Path
import shutil
from .tools import random_str

_SIZE_UNITS = {'gb':1073741824, 'mb':1048576, 'kb':1024, 'b':1}

def _dir_slash(dirpath:str)->str:
	''' Adds trailing slash if there is's not there. '''
	if dirpath.endswith('\\'):
		return dirpath
	else:
		return dirpath + '\\'

def file_read(fullpath:str, encoding:str='utf-8')->str:
	''' Returns content of file '''
	if encoding == 'binary':
		with open(fullpath, 'rb') as f:
			return f.read()
	else:
		with open(fullpath, 'tr', encoding=encoding) as f:
			return f.read()

def file_write(fullpath:str, content:str, encoding:str='utf-8'):
	''' Save content to file. Create file if the fullpath doesn't exist.
	'''
	if encoding == 'binary':
		with open(fullpath, 'wb+') as f:
			f.write(content)
	else:
		with open(fullpath, 'wt+', encoding=encoding, errors='ignore') as f:
			f.write(content)

def file_rename(fullpath:str, dest:str)->str:
	''' Rename path.
		dest - fullpath or just new file name without parent directory.
	'''
	if not ':' in dest: dest = os.path.dirname(fullpath) + '\\' + dest
	os.rename(fullpath, dest)
	return dest

dir_rename = file_rename

def file_log(fullpath:str, message:str, encoding:str='utf-8'
				, time_format:str='%Y.%m.%d %H:%M:%S'):
	with open(fullpath, 'at+', encoding=encoding) as f:
		f.write(time.strftime(time_format) + '\t' + message + '\n')

def file_copy(fullpath:str, destination:str):
	''' Copies file to destination.
		Destination may be fullpath or folder name.
		If destination file exists it will be overwritten.
		If destination is a folder, subfolders will
		be created if they don't exist.
	'''
	try:
		shutil.copy(fullpath, destination)
	except FileNotFoundError:
		try:
			os.makedirs(
				os.path.dirname(destination)
			)
			shutil.copy(fullpath, destination)
		except FileExistsError: pass

def file_move(fullpath:str, destination:str):
	''' Move file to destination.
		Destination may be fullpath or folder name.
		If destination path exist it will be overwritten.
	'''
	if os.path.isdir(destination):
		new_fullpath = _dir_slash(destination) + os.path.basename(fullpath)
	else:
		new_fullpath = destination
	try:
		os.remove(new_fullpath)
	except FileNotFoundError:
		pass
	shutil.move(fullpath, new_fullpath)

def file_delete(fullpath:str):
	try:
		os.remove(fullpath)
	except FileNotFoundError:
		pass

def dir_copy(fullpath:str, destination:str, update:bool=True):
	''' Copy a folder with all content to a new location.
		Returns number of errors.
	'''
	err = 0
	try:
		dir_util.copy_tree(fullpath, destination, update=update)
	except dir_util.DistutilsFileError as e:
		err += 1
		print(f'dir_copy error: {repr(e)}')
	return err

def dir_create(fullpath:str=None)->str:
	''' Creates new dir and returns full path.
		If fullpath=None then creates temporary directory.
	'''
	if not fullpath: return temp_dir('temp')
	try:
		os.makedirs(fullpath)
	except FileExistsError: pass
	return fullpath

def dir_delete(fullpath:str):
	try:
		shutil.rmtree(fullpath)
	except FileNotFoundError:
		pass

def dir_exists(fullpath:str)->bool:
	return os.path.isdir(fullpath)

def file_exists(fullpath:str)->bool:
	return os.path.isfile(fullpath)

def path_exists(fullpath:str)->bool:
	''' Check if directory or file exist '''
	p = Path(fullpath)
	return p.exists()

def file_size(fullpath:str, unit:str='b')->int:
	e = _SIZE_UNITS.get(unit.lower(), 1)
	return os.stat(fullpath).st_size // e

def file_ext(fullpath:str)->str:
	''' Returns file extension without dot. '''
	ext = os.path.splitext(fullpath)[1]
	if ext == '': return ext
	return ext[1:]

def dir_purge(fullpath:str, days:int=0, recursive:bool=False
			, creation:bool=False, test:bool=False):
	''' Deletes files older than x days.
		Returns number of deleted files and folders. 
		days=0 - delete everything
		creation - use date of creation, otherwise use last
			modification date.
		recursive - delete in subfolders too. Empty subfolders 
			will be deleted.
		test - only print files and folders that should be removed.
	'''
	counter = 0
	def robust_remove_file(fullpath):
		nonlocal counter
		try:
			os.remove(fullpath)
			counter += 1
		except PermissionError:
			try:
				os.chmod(fullpath, stat.S_IWRITE)
				os.remove(fullpath)
				counter += 1
			except:
				pass
		except:
			pass
	def robust_remove_dir(fullpath):
		nonlocal counter
		try:
			shutil.rmtree(fullpath)
			counter += 1
		except:
			pass
	def file_print(fullpath):
		nonlocal counter
		counter += 1
		print(os.path.basename(fullpath))
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

def file_name(fullpath:str)->str:
	''' Returns only name from fullpath
	'''
	return os.path.basename(fullpath)

def file_dir(fullpath:str)->str:
	''' Returns directory from fullpath
	'''
	return os.path.dirname(fullpath)
		
def file_backup(fullpath:str, folder:str=None):
	''' Copy somefile.txt to somefile_2019-05-19_21-23-02.txt
		folder - destination. If not specified - current folder
	'''
	timestamp = time.strftime('%y-%m-%d_%H-%M-%S')
	fi_pa = Path(fullpath)
	if folder:
		folder = Path(folder)
	else:
		folder = fi_pa.parent
	if not folder.exists(): folder.mkdir(parents=True, exist_ok = True)
	destination = (
		str(folder) + '\\'
		+ '.'.join(fi_pa.name.split('.')[0:-1])
		+ '_' + timestamp
		+ fi_pa.suffix
	)
	shutil.copy(fullpath, destination)

def free_space(letter:str, unit:str='GB')->int:
	''' Returns disk free space in GB, MB, KB or B
	'''
	e = _SIZE_UNITS.get(unit.lower(), 1073741824)
	return shutil.disk_usage(f'{letter}:\\')[2] // e

def dir_list(fullpath:str)->list:
	''' Returns list of files in specified folder.
		Fullpath passed to glob.glob
	'''
	recursive = ('**' in fullpath)
	return glob.glob(fullpath, recursive=recursive)

def csv_read(fullpath:str, encoding:str='utf-8', fieldnames:tuple=None
, delimiter:str=';', quotechar:str='"')->list:
	''' Read whole CSV file and return content as list of dictionaries.
		If no fieldnames is provided uses first row as fieldnames.
		All cell values is strings.
	'''
	with open(fullpath, 'r', encoding=encoding) as f:
		reader = csv.DictReader(f, skipinitialspace=True, fieldnames=fieldnames
		, delimiter=delimiter, quotechar=quotechar)
		li = [dict(row) for row in reader]
	return li

def csv_write(fullpath:str, content:list, fieldnames:tuple=None
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

def dir_size(fullpath:str, unit:str='b')->int:
	e = _SIZE_UNITS.get(unit.lower(), 1)
	total_size = 0
	for dirpath, _, filenames in os.walk(fullpath):
		for fi in filenames:
			fp = os.path.join(dirpath, fi)
			if not os.path.islink(fp):
				total_size += os.path.getsize(fp)
	return total_size // e

def dir_zip(fullpath:str, destination:str)->str:
	''' Compresses folder and returns the full path to archive.
	'''
	filename = os.path.basename(destination)
	name, suffix = filename.split('.')
	archive_from = os.path.dirname(fullpath)
	archive_to = os.path.basename(fullpath.strip(os.sep))
	shutil.make_archive(name, format=suffix, root_dir=archive_from
						, base_dir=archive_to)
	shutil.move(f'{name}.{suffix}', destination)
	return destination

def file_zip(fullpath, destination:str)->str:
	''' Compresses a file or files to archive.
		fullpath - string with fullpath or list with fullpaths.
		destination - fullpath to the archive.
	'''
	if type(fullpath) is str:
		with zipfile.ZipFile(
			destination, 'w'
		) as zipf:
			zipf.write(fullpath, arcname=os.path.basename(fullpath)
						, compress_type=zipfile.ZIP_DEFLATED)
		return destination
	elif type(fullpath) is list:
		with zipfile.ZipFile(
			destination, 'w'
		) as zipf:
			for fi in fullpath:
				zipf.write(fi, arcname=os.path.basename(fi)
						, compress_type=zipfile.ZIP_DEFLATED)
		return destination
	else:
		return 'error: unknown type of fullpath'

def temp_dir(new_dir:str=None)->str:
	''' Returns full path of temp dir (without trailing slash).
		If new_dir - creates folder in temp dir and returns its full path.
	'''
	if not new_dir:
		return tempfile.gettempdir()
	if new_dir == 'temp':
		new_dir = (tempfile.gettempdir()
			+ '\\' + time.strftime("%m%d%H%M%S") + random_str(5))
	else:
		new_dir = tempfile.gettempdir() + '\\' + new_dir
	try:
		os.mkdir(new_dir)
	except FileExistsError: pass
	return new_dir

def temp_file(suffix:str='')->str:
	''' Returns temporary file name. '''
	return (tempfile.gettempdir() + '\\'
			+ time.strftime('%m%d%H%M%S') + random_str(5) + suffix)

def file_hash(fullpath:str, algorithm:str='crc32')->str:
	''' Returns hash of file.
		algorithm - 'crc32' or 'md5'.
	'''
	algorithm = algorithm.lower()
	if algorithm == 'md5':
		hash_md5 = hashlib.md5()
		with open(fullpath, 'rb') as fi:
			for chunk in iter(lambda: fi.read(4096), b''):
				hash_md5.update(chunk)
		return hash_md5.hexdigest()
	elif algorithm == 'crc32':
		prev = 0
		for eachLine in open(fullpath,"rb"):
			prev = crc32(eachLine, prev)
		return '%X' % (prev & 0xFFFFFFFF)		
	else:
		return 'error: unknown algorithm'
