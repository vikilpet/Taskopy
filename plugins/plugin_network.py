import os
import socket
import requests
import urllib
import lxml.html
import tempfile
from hashlib import md5
from bs4 import BeautifulSoup
import json
import datetime
import warnings
import threading
import json2html
from .tools import dev_print, time_sleep, tdebug \
, locale_set


_USER_AGENT = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36'}

def page_get(url:str, encoding:str='utf-8', session:bool=False
, cookies:dict=None, headers:dict=None
, http_method:str='get', json_data:str=None
, post_file:str=None, post_hash:bool=False
, post_form_data:dict=None, timeout:int=3
, attempts:int=3, safe=False, **kwargs)->str:
	''' Gets content of the specified URL '''
	if (post_file or post_form_data): http_method = 'POST'
	if http_method: http_method = http_method.lower()
	args = {'url': url, 'json': json_data, 'timeout': timeout
		, 'data': post_form_data}
	file_obj = None
	post_file_hash = None
	if post_file:
		if not os.path.isfile(post_file):
			return Exception('The post file does not exist')
		if post_hash:
			post_file_hash = _file_hash(post_file)
		file_obj = open(post_file, 'rb')
		args['files'] = {'file': file_obj}
	else:
		post_file_hash = False
	if session:
		req_obj = requests.Session()
		req_obj.headers.update(_USER_AGENT)
		if headers: req_obj.headers.update(headers)
		if cookies: req_obj.cookies.update(cookies)
		if post_file_hash:
			req_obj.headers.update(
				{'Content-MD5': post_file_hash})
	else:
		req_obj = requests
		if cookies: args['cookies'] = cookies
		args['headers'] = {**_USER_AGENT}
		if post_file_hash:
			args['headers']['Content-MD5'] = post_file_hash
	for attempt in range(attempts):
		try:
			time_sleep(attempt)
			req = getattr(req_obj, http_method)(**args, **kwargs)
			if req.status_code >= 500:
				continue
			elif req.status_code in [403, 404]:
				break
			else:
			 	break
		except Exception as e:
			if isinstance(e, requests.exceptions.SSLError):
				return e
			tdebug(f'failed again ({attempt}).'
				,  f'Error: {repr(e)}\nurl={url}')
			pass
	else:
		raise Exception(
			f'no more attempts ({attempts}) {url[:100]}')
	if file_obj: file_obj.close()
	content = str(req.content
	, encoding=encoding, errors='ignore')
	return content

def html_whitespace(text:str)->str:
	''' Removes whitespace characters from string.
	'''
	if text is None:
		return text
	return ' '.join(text.split())

def file_download(url:str, destination:str=None
, attempts:int=3, timeout:int=1
, del_bad_file:bool=False, headers:dict={}
, safe=False, size_limit:int=None
, stop_event:threading.Event=None
, **kwargs)->str:
	''' Download file from url to destination and return fullpath.
		Returns a full path to the downloaded file.
		attempts - how many times to retry download if failed.
		If destination is a folder, then get filename from url.
		If destination is None then download to temporary file.

		stop_event - threading event to stop download.

		Use 'Range' header to download first n bytes (server should
		support this header):
			headers = {'Range': 'bytes=0-1024'} 
	'''
	CHUNK_SIZE = 1_048_576
	if isinstance(destination, (list, tuple)):
		destination = os.path.join(*destination)
		try:
			os.makedirs(os.path.dirname(destination))
		except FileExistsError:
			pass
	if destination is None:
		dest = tempfile.TemporaryFile()
	elif os.path.isdir(destination):
		dest = open(
			os.path.join(destination, url.split('/')[-1])
			, 'bw+'
		)
	else:
		dest = open(destination, 'bw+')
	dest_file = dest.name
	dest.close()
	for attempt in range(attempts):
		try:
			req = requests.get(
				url, stream=True, timeout=timeout
				, headers={**_USER_AGENT, **headers}
				, **kwargs
			)
			with open(dest_file, 'wb+') as fd:
				cur_size = 0
				for chunk in req.iter_content(chunk_size=CHUNK_SIZE):
					fd.write(chunk)
					if stop_event and stop_event.is_set(): break
					if not size_limit: continue
					cur_size += len(chunk)
					if size_limit <= cur_size: break
			break
		except Exception as e:
			tdebug(f'dl attempt {attempt} failed'
				+ f', err="{repr(e)[:50]}...", url={url[-30:]}')
	else:
		if del_bad_file:
			try:
				os.remove(dest_file)
			except Exception as e:
				dev_print('Couldn not delete a bad file: ' + str(e))
		raise Exception(f'No more attempts ({attempt}), url={url[:100]}')
	return dest_file

def html_clean(html_str:str, separator=' ')->str:
	''' Removes HTML tags from string '''
	warnings.filterwarnings("ignore", category=UserWarning, module='bs4')
	soup = BeautifulSoup(html_str, 'html.parser')
	return soup.get_text(separator=separator)

def html_element(url:str, element
, clean: bool = True, element_num: int = 0
, safe=False, **kwargs)->str:
	''' Get text of specified page element (div).
		Returns str or list of str.
		url - URL or string with HTML.
		element - dict (list of dictionaries)
			, or str (list of strings). If 'element' is a list
			then 'html_element' returns list of found elements.
			If it's a dict or list of dicts then method find_all
			of Beautiful Soup will be used.
			If it's a str or list of str then xpath will be used.
			Example for Soup:
				element={
					'name': 'span'
					, 'attrs': {'itemprop':'softwareVersion'}
				}
			Example for xpath:
				element='/html/body/div[1]/div/div'
		clean - remove html tags and spaces (Soup).
		kwargs - additional arguments for page_get.
	'''
	if not url[:4].lower().startswith('http'):
		html = url
	else:
		status, html = page_get(url=url, safe=True, **kwargs)
		if not status: raise html
	if isinstance(element, list):
		element_li = element
	else:
		element_li = [element]
	result = []
	if isinstance(element_li[0], dict):
		parser = BeautifulSoup(html, 'html.parser')
	elif element_li[0].startswith('/'):
		parser = lxml.html.fromstring(html
			, parser=lxml.html.HTMLParser(recover=True))
	else:
		parser = parser = BeautifulSoup(html, 'html.parser')
	for elem in element_li:
		if isinstance(parser, BeautifulSoup):
			if len(element_li) == 1:
				el_num = element_num
			else:
				el_num = 0
			if isinstance(elem, dict):
				found_elem = parser.find_all(**elem)
			else:
				found_elem = parser.select(elem)
			if found_elem:
				if clean:
					result.append( html_whitespace(
						found_elem[el_num].get_text()
					))
				else:
					result.append( str(found_elem[el_num]) )
			else:
				raise Exception('html_element: element not found')
		else:
			if len(element_li) == 1:
				el_num = element_num
			else:
				el_num = 0
			found_elem = parser.xpath(elem)[el_num]
			if isinstance(found_elem, str):
				if clean:
					result.append( html_whitespace(found_elem) )
				else:
					result.append(found_elem)
			else:
				if clean:
					result.append(
						html_whitespace(found_elem.text_content())
					)
				else:
					result.append(
						lxml.etree.tostring(found_elem, encoding=str)
					)
	if len(element_li) == 1:
		return result[0]
	else:
		return result

def json_element(source:str, element:list=None
, safe=False, **kwargs):
	''' Download JSON by url and get its nested element by
			map of keys like ['list', 0, 'someitem', 1]
		source - URL to download or string with JSON.
		element - can be a None, list or list of lists so it will
		get every element specified in nested list and return
		list of values.
		If None - just return serialized JSON.
			examples:
				element=['banks', 0, 'usd', 'sale']
					result: 63.69
				
				element=[
					['banks', 0, 'eur', 'sale']
					, ['banks', 0, 'usd', 'sale']
					, ['banks', 0, 'gbp', 'sale']
				]
					result = [71.99, 63.69, 83.0]
		If nothing found then return exception.
		kwargs - additional arguments for page_get.
	'''
	if source.lower().startswith('http'):
		status, j = page_get(url=source, safe=True, **kwargs)
		if not status: raise j
	else:
		j = source
	data = json.loads(j)
	if element is None: return data
	if isinstance(element[0], list):
		li = []
		try:
			for elem in element:
				da = data
				for key in elem: da = da[key]
				li.append(da)
			r = li
		except:
			raise Exception('element not found')
	else:
		try:
			for key in element: data = data[key]
			r = data
		except:
			raise Exception('element not found')
	return r

def xml_element(url:str, element:str
, element_num:int=0, encoding:str='utf-8'
, safe=False, **kwargs):
	'''	Download the XML document from the specified URL and get the value
		by the list with 'map' of parent elements like ['foo', 'bar']
		
		element - XPath or list of XPath's.
		Example: element='/result/array/msgContact[1]/msgCtnt'

		kwargs - additional arguments for page_get.
	'''
	if url.startswith('http'):
		status, content = page_get(url=url, **kwargs)
		if not status: raise content
	else:
		status = True
		content = url
	if isinstance(element, list):
		element_li = element
	else:
		element_li = [element]
	result = []
	tree = lxml.etree.fromstring(content.encode(encoding=encoding))
	for element in element_li:
		value = tree.xpath(element)[element_num]
		if value != None:
			result.append(value.text)
		else:
			raise Exception(f'xml_element: element not found: {element}')
	if isinstance(element, list):
		return result
	else:
		return result[0]

def tracking_status_rp(track_number:str, safe=False)->str:
	''' Get last status of Russian post parcel 
	'''
	url = r'https://www.pochta.ru/tracking?p_p_id=trackingPortlet_WAR_portalportlet&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=getList&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_pos=1&p_p_col_count=2&barcodeList={}&pos'
	status_list = json_element(
		url.format(track_number)
		, [
			[
				'list',0,'trackingItem', 'trackingHistoryItemList', 
				0, 'description'
			]
			, [
				'list',0,'trackingItem', 'trackingHistoryItemList'
				, 0, 'humanStatus'
			]
		]
		, headers={'Accept-Language':'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'}
	)
	return ', '.join(status_list)

def domain_ip(domain:str)->list:
	''' Get IP adresses of domain
	'''
	data = socket.gethostbyname_ex(domain)
	return data[2]



def url_hostname(url:str, second_lvl:bool=True)->str:
	''' Get hostname (second level domain) from URL.
	'''
	domain = urllib.parse.urlparse(url).netloc
	if not second_lvl: return domain
	if '.'.join(domain.split('.')[-2:]) in ['co.uk']:
		suf_len = -3
	else:
		suf_len = -2
	domain = '.'.join(domain.split('.')[suf_len:])
	return domain



def is_online(*sites, timeout:int=2)->int:
	''' Checks if there is an internet connection using HEAD
		requests to the specified web sites.
	'''
	if not sites: sites = ['https://www.google.com/'
		, 'https://yandex.ru/']
	r = 0
	for site in sites:
		try:
			requests.head(site, timeout=timeout
				, headers={**_USER_AGENT})
			r += 1
		except: pass
	return r

def _file_hash(fullpath:str)->str:
	hash_md5 = md5()
	with open(fullpath, 'rb') as fi:
		for chunk in iter(lambda: fi.read(4096), b''):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()

def pc_name()->str:
	''' Returns hostname of current computer '''
	return socket.gethostname()

def json_to_html(json_data, **kwargs)->str:
	''' Convert json to HTML table with
		module json2html '''
	return json2html.json2html.convert(
		json=json_data, **kwargs)

def http_header(url:str, header:str, **kwargs)->str:
	'''
	Get HTTP header of URL or get them all (as a dictionary)
	if header=='all'.
	'''
	headers={**_USER_AGENT, **kwargs.get('headers', {}) }
	req = requests.head(url, headers=headers, **kwargs)
	if header == 'all': return req.headers
	return req.headers.get(header)

def http_h_last_modified(url:str, **kwargs):
	'HTTP Last Modified time in datetime format'
	date_str = http_header(url, header='Last-Modified', **kwargs)
	with locale_set('C'):
		return datetime.datetime.strptime(date_str
			, '%a, %d %b %Y %H:%M:%S GMT')

def port_scan(host:str, port:int
, timeout:float=0.5)->bool:
	' Scan TCP port '
	SUCCESS = 0
	sock = socket.socket()
	sock.settimeout(timeout)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	connected = sock.connect_ex((host, port)) is SUCCESS
	sock.close()
	return connected

