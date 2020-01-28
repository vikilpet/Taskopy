import os
import socket
import requests
import urllib
import lxml.etree
import tempfile
from hashlib import md5
from bs4 import BeautifulSoup
import json
import warnings
from .tools import dev_print, decor_except, ManualException


@decor_except
def page_get(url:str, encoding:str='utf-8', session:bool=False
, cookies:dict=None, headers:dict={}
, http_method:str='get', json_data:str=None
, post_file:str=None, post_hash:bool=False
, post_form_data:dict=None, timeout:tuple=(10, 600))->str:
	''' Gets content of the specified URL '''
	if (post_file or post_form_data): http_method = 'POST'
	if http_method: http_method = http_method.lower()
	args = {'url': url, 'json': json_data, 'timeout': timeout
		, 'data': post_form_data}
	file_obj = None
	post_file_hash = None
	if post_file:
		if post_hash: post_file_hash = _file_hash(post_file)
		file_obj = open(post_file, 'rb')
		args['files'] = {'file': file_obj}
	else:
		post_file_hash = False
	if session:
		req_obj = requests.Session()
		if headers: req_obj.headers.update(headers)
		if cookies: req_obj.cookies.update(cookies)
		if post_file_hash: req_obj.headers.update(
			{'Content-MD5': post_file_hash})
	else:
		req_obj = requests
		args['cookies'] = cookies
		if post_file_hash:
			headers['Content-MD5'] = post_file_hash
		args['headers'] = headers
	req = getattr(req_obj, http_method)(**args)
	if file_obj: file_obj.close()
	if req.status_code == 200:
		return str(req.content, encoding=encoding, errors='ignore')
	else:
		return req.status_code

def html_whitespace(text:str)->str:
	''' Removes whitespace characters from string.
	'''
	if text is None:
		return text
	return ' '.join(text.split())

@decor_except
def file_download(url:str, destination:str=None, attempts:int=3)->str:
	''' Download file from url to destination and return fullpath.
		Returns the full path to the downloaded file.
		attempts - how many times to retry download if failed.
		If destination is a folder, then get filename from url.
		If destination is None then download to temporary file.
	'''
	if destination is None:
		dest = tempfile.TemporaryFile()
	elif os.path.isdir(destination):
		dest = open(
			destination + '\\' + url.split('/')[-1]
			, 'bw+'
		)
	else:
		dest = open(destination, 'bw+')
	dest_file = dest.name
	dest.close()
	for attempt in range(attempts):
		try:
			urllib.request.urlretrieve (url, dest_file)
		except Exception as e:
			dev_print(f'{attempt} dl failed, err="{repr(e)[:20]}", url={url}')
		else:
			break
		finally:
			if (attempt + 1) >= attempts:
				raise ManualException('No more attempts')
	return dest_file

def html_clean(html_str:str, separator=' ')->str:
	''' Removes HTML tags from string '''
	warnings.filterwarnings("ignore", category=UserWarning, module='bs4')
	text = BeautifulSoup(html_str, 'html.parser'
		).get_text(separator=separator)
	return text

@decor_except
def html_element(url:str, element, number:int=0
, clean:bool=True , encoding:str='utf-8'
, session:bool=False, headers:dict=None
, http_method:str='GET', post_form_data:dict=None
, cookies:dict=None)->str:
	''' Get text of specified page element (div).
		element - dict that will passed to find_all method:
			https://www.crummy.com/software/BeautifulSoup/bs4/doc/
			Or it can be a list of dicts.
			Or it can be string with xpath.
			Example for 'find_all':
				element={
					'name': 'span'
					, 'attrs': {'itemprop':'softwareVersion'}
				}
			Example for xpath:
				element='/html/body/div[1]/div/div'

		number - number of an element in the list of similar elements.
		clean - remove html tags and spaces.
		headers - optional dictionary with request headers.
		session - use requests.Session instead of get.
		cookies - dictionary with cookies
			like {'GUEST_LANGUAGE_ID': 'ru_RU'}
	'''
	html = page_get(url=url, encoding=encoding, session=session
	, cookies=cookies, headers=headers, http_method=http_method
	, post_form_data=post_form_data)
	if isinstance(html, Exception): return html
	if isinstance(element, list):
		soup = BeautifulSoup(html, 'html.parser')
		r = []
		for d in element:
			r += soup.find_all(**d)
		if r:
			if clean:
				return [html_whitespace(i.get_text()) for i in r]
			else:
				return [str(i) for i in r]
		else:
			raise ManualException('element not found')
	elif isinstance(element, dict):
		soup = BeautifulSoup(html, 'html.parser')
		r = soup.find_all(**element)
		if r:
			if clean:
				r = r[number].get_text()
				return html_whitespace(r)
			else:
				return str(r[number])
		else:
			raise ManualException('element not found')
	elif isinstance(element, str):
		tree = lxml.etree.fromstring(html
		, parser=lxml.etree.HTMLParser(recover=True))
		tree_elem = tree.xpath(element)[number]
		if isinstance(tree_elem, str):
			return html_whitespace(tree_elem)
		else:
			return html_whitespace(tree_elem.text)

@decor_except
def json_element(source:str, element:list=None, headers:dict=None
, session:bool=False, cookies:dict=None
, http_method:str='GET', json_data:str=None):
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
		headers - optional dictionary with request headers
		session - use requests.Session instead of get
		cookies - dictionary with cookies like {'GUEST_LANGUAGE_ID': 'ru_RU'}
	'''
	if source.startswith('http'):
		j = page_get(
			url=source
			, session=session
			, headers=headers
			, cookies=cookies
			, http_method=http_method
			, json_data=json_data
		)
		if isinstance(j, Exception):
			if isinstance(element[0], list):
				return [repr(j)]
			else:
				return repr(j)
	else:
		j = source
	data = json.loads(j)
	if element is None:
		return data
	if type(element[0]) is list:
		li = []
		try:
			for elem in element:
				da = data
				for key in elem: da = da[key]
				li.append(da)
			r = li
		except:
			r = ['element not found']
	else:
		try:
			for key in element: data = data[key]
			r = data
		except:
			r = 'element not found'
	return r



@decor_except
def tracking_status_rp(track_number:str)->str:
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
	if not sites: sites = ['https://www.google.com/', 'https://yandex.ru/']
	r = 0
	for site in sites:
		try:
			requests.head(site, timeout=timeout)
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