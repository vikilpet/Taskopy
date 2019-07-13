import os
import time
import glob
from pathlib import Path
import shutil

_SIZE_PREFIXES = {'gb':1073741824, 'mb':1048576, 'kb':1024, 'b':1}

def file_read(fullpath:str)->str:
	''' Returns content of file '''
	with open(fullpath, 'tr') as f: return f.read()

def file_write(fullpath:str, content:str):
	''' Save content in file. Create file if fullpath doesn't exist.
	'''
	with open(fullpath, 'wt+') as f:
		f.write(content)

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
	e = _SIZE_PREFIXES.get(unit.lower(), 1)
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
i		recursive - delete in subfolders too. Empty subfolders 
			will be deleted.
		test - only print files and folders that should be removed
	'''
	def robust_remove(fullpath):
		try:
			os.remove(fullpath)
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
		file_func = robust_remove
		dir_func = shutil.rmtree
	
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
		
def file_backup(fullpath, folder:str=None):
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
	e = _SIZE_PREFIXES.get(unit.lower(), 1073741824)
	return shutil.disk_usage(f'{letter}:\\')[2] // e

def dir_list(fullpath:str)->list:
	''' Returns list of files in specified folder.
		Fullpath passed to glob.glob
	'''
	recursive = ('**' in fullpath)
	return glob.glob(fullpath, recursive=recursive)
