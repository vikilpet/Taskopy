import os
import time
import glob
import csv
import zipfile
import tempfile
from pathlib import Path
import pyodbc
import shutil
from .tools import random_str

_SIZE_UNITS = {'gb':1073741824, 'mb':1048576, 'kb':1024, 'b':1}

def file_read(fullpath:str, encoding:str='utf-8')->str:
	''' Returns content of file '''
	with open(fullpath, 'tr', encoding=encoding) as f: return f.read()

def file_write(fullpath:str, content:str, encoding:str='utf-8'):
	''' Save content in file. Create file if fullpath doesn't exist.
	'''
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
	''' Copy file to destination.
		Destination may be fullpath or folder name.
		If destination path exist it will be overwritten.
		If destination is a folder, it should exist.
	'''
	shutil.copy(fullpath, destination)

def file_move(fullpath:str, destination:str):
	''' Move file to destination.
		Destination may be fullpath or folder name.
		If destination path exist it will be overwritten.
	'''
	if os.path.exists(destination):
		if not os.path.isdir(destination):
			os.remove(destination)
	shutil.move(fullpath, destination)

def file_delete(fullpath:str):
	try:
		os.remove(fullpath)
	except FileNotFoundError:
		pass

def dir_delete(fullpath:str):
	try:
		shutil.rmtree(fullpath)
	except FileNotFoundError:
		pass

def path_exists(fullpath:str)->bool:
	''' Check if directory or file exist '''
	p = Path(fullpath)
	return p.exists()

def file_size(fullpath:str, unit:str='b')->int:
	e = _SIZE_UNITS.get(unit.lower(), 1)
	return os.stat(fullpath).st_size // e
	retudir.exists()

def file_size(fullpath:str, unit:str='b')->int:
	e = _SIZE_UNITS.get(unit.lower(), 1)
	return os.stat(fullpath).st_size // e

def is_directory(fullpath:str)->bool:
	''' Check if fullpath is a directory '''
	p = Path(fullpath)
	return p.is_dir()

def purge_old(fullpath:str, days:int=0, recursive=False
			, creation:bool=False, test:bool=False):
	''' Delete files older than x days.
		days=0 - delete everything
		creation - use date of creation, otherwise use last
			modification date.
		recursive - delete in subfolders too. Empty subfolders 
			will be deleted.
		test - only print files and folders that should be removed
	'''
	def robust_remove_file(fullpath):
		try:
			os.remove(fullpath)
		except:
			pass
	def robust_remove_dir(fullpath):
		try:
			shutil.rmtree(fullpath)
		except:
			pass
	if days: delta = 24 * 3600 * days
	if creation:
		date_func = os.path.getctime
	else:
		date_func = os.path.getmtime
	if fullpath[-1] != '\\': fullpath += '\\'
	if recursive:
		files = glob.glob(f'{fullpath}**\*', recursive=True)
	else:
		files = glob.glob(f'{fullpath}*')
	current_time = time.time()
	if test:
		file_func = print
		dir_func = print
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
				if (current_time - date_func(fi)) > delta:
					file_func(fi)
			else:
				file_func(fi)

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

def csv_read(fullpath:str, encoding:str='utf-8', fieldnames=None, delimiter:str=';', quotechar:str='"')->list:
	''' Read whole CSV file and return content as list of dictionaries
	'''
	with open(fullpath, 'r', encoding=encoding) as f:
		reader = csv.DictReader(f, skipinitialspace=True, fieldnames=fieldnames
		, delimiter=delimiter, quotechar=quotechar)
		li = [dict(row) for row in reader]
	return li

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

def temp_folder()->str:
	''' Returns full path of temp folder (without trailing slash).
	'''
	return tempfile.gettempdir()

def temp_file(suffix:str='')->str:
	''' Returns temporary file name.
	'''
	return (f'{tempfile.gettempdir()}\\'
			+ f'{time.strftime("%m%d%H%M%S") + random_str(5) + suffix}')