import os
import socket
import requests
import urllib
import lxml.html
import re
import html
import tempfile
from hashlib import md5
from bs4 import BeautifulSoup
import json
import datetime
import warnings
import threading
import json2html
from .tools import dev_print, time_sleep, tdebug \
, locale_set, safe, patch_import, value_to_unit

_USER_AGENT = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36'}

def http_req(url:str, encoding:str='utf-8', session:bool=False
, cookies:dict=None, headers:dict=None
, http_method:str='get', json_data:str=None
, post_file:str=None, post_hash:bool=False
, post_form_data:dict=None, timeout:int=3
, attempts:int=3, **kwargs)->str:
	'''
	Gets content of the specified URL
	
	Skip SSL verification: `verify=False`
	Follow redirects: `allow_redirects=True`
	'''
	if (post_file or post_form_data): http_method = 'POST'
	if http_method: http_method = http_method.lower()
	args = {'url': url, 'json': json_data, 'timeout': timeout}
	if post_form_data: args['data'] = post_form_data
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
		if headers: args['headers'].update(headers)
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
			if isinstance(e, requests.exceptions.InvalidHeader):
				return e
			if isinstance(e, TypeError):
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
	'''
	Removes an excessive white space from the string.
	'''
	if not text: return text
	return ' '.join(text.split())
_js_regex = re.compile(r"(\".*?\"|\'.*?\')|(/\*.*?\*/|//[^\r\n]*$)"
, re.MULTILINE|re.DOTALL)
def _js_remove_comments(string):
	def _replacer(match):
		if match.group(2) is not None:
			return "" # so we will return empty to remove the comment
		else: # otherwise, we will return the 1st group
			return match.group(1) # captured quoted-string
	return _js_regex.sub(_replacer, string)

_re_html = re.compile(r'(<!--.*?-->)', flags=re.DOTALL)
_re_css = re.compile(r'!/\*[^*]*\*+([^/][^*]*\*+)*/!')
_re_white_space = re.compile(r">\s*<")
_re_js = re.compile('<script>.+?</script>', flags=re.DOTALL)
def html_minify(html:str)->str:
	'''
	Removes HTML, javascript and CSS comments and whitespace.
	'''
	html = _re_html.sub('', html)
	js_blocks = _re_js.findall(html)
	for block in js_blocks:
		html = html.replace(block, _js_remove_comments(block))
	html = _re_css.sub('', html)
	html = _re_white_space.sub('><', html)
	return html_whitespace(html)


def file_download(url:str, destination:str=None
, attempts:int=3, timeout:int=1
, del_bad_file:bool=False, headers:dict={}
, size_limit:int=None
, stop_event:threading.Event=None
, overwrite:bool=False
, chunk_size:int=1_048_576
, **kwargs)->str:
	''' Download file from url to destination and return fullpath.
		Returns a full path to the downloaded file.
		
		*attempts* - how many times to retry download if failed.
		*destination* - file, directory or None. If the latter,
		download to a temporary folder.

		*overwrite* - overwrite file if exists.

		*stop_event* - `threading` event to stop download.

		In case of an exception, the exception object has a *fullpath* attribute
		, so it is possible to do something with it. Example:

			status, data = safe(file_download)('https://...')
			if status:
				tprint('successfull download:', data)
			else:
				tprint(
					'all that we got:', data.fullpath
					, 'due to error:', repr(data)
				)
			

		Use 'Range' header to download first n bytes (server should
		support this header):

			headers = {'Range': 'bytes=0-1024'}

	'''
	if isinstance(destination, (list, tuple)):
		destination = os.path.join(*destination)
		try:
			os.makedirs(os.path.dirname(destination))
		except FileExistsError:
			pass
	find_name = False
	dst_file = destination
	if dst_file:
		find_name = os.path.isdir(dst_file)
	else:
		find_name = True
		dst_file = tempfile.gettempdir()
	last_exc = None
	for attempt in range(attempts):
		try:
			req = requests.get(
				url, stream=True, timeout=timeout
				, headers={**_USER_AGENT, **headers}
				, **kwargs
			)
			if find_name:
				fname = ''
				try:
					fname = req.headers.get('content-disposition', '') \
						.split('filename=')[1]
				except Exception as e:
					tdebug(f'content-disposition error: {e}')
					fname = req.url.split('/')[-1]
				if fname:
					dst_file = os.path.join(dst_file, fname)
				else:
					with tempfile.TemporaryFile() as f:
						dst_file = f.name
			if os.path.isfile(dst_file) and not overwrite:
				return dst_file
			with open(dst_file, 'wb+') as fd:
				cur_size = 0
				for chunk in req.iter_content(chunk_size=chunk_size):
					fd.write(chunk)
					if stop_event and stop_event.is_set(): break
					if not size_limit: continue
					cur_size += len(chunk)
					if size_limit <= cur_size: break
			break
		except Exception as e:
			last_exc = e
			tdebug(f'dl attempt {attempt} failed'
				+ f', err="{repr(e)[:50]}...", url={url[-30:]}')
	else:
		if del_bad_file:
			try:
				os.remove(dst_file)
			except Exception as e:
				dev_print('Couldn not delete a bad file: ' + str(e))
		last_exc.fullpath = dst_file
		raise last_exc
	return dst_file

def html_clean(html_str:str, separator=' ')->str:
	''' Removes HTML tags from string '''
	warnings.filterwarnings("ignore", category=UserWarning, module='bs4')
	soup = BeautifulSoup(html_str, 'html.parser')
	return soup.get_text(separator=separator)

def html_element(url:str, element
, clean:bool=True, element_num:int=0
, attrib:str=None, **kwargs)->str:
	'''
	Get text of specified page element (div).
	Returns str or list of str.
	url - URL or string with HTML.
	attrib - get specific attribute from element (TODO: not only for 'all').
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
	kwargs - additional arguments for http_req.

	XPath cheatsheet: https://devhints.io/xpath
	XPath examples:
		'//div[@id="id"]/p'
		'//div[contains(@class, "main")]/div/script'
		'//table[2]/thead/tr/th[2]'
	'''
	if not url[:4].lower().startswith('http'):
		html = url
	else:
		status, html = safe(http_req)(url=url, **kwargs)
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
	if element_num == 'all':
		found_elem = parser.find_all(**element)
		if found_elem:
			if clean:
				if attrib:
					return [ e.get(attrib, None) for e in found_elem ]
				else:
					return [ 
						html_whitespace(e.get_text())
							for e in found_elem
					]
			else:
				if attrib:
					return [ e.get(attrib, None) for e in found_elem ]
				else:
					return list(map(str, found_elem))
		else:
			raise Exception('html_element: element not found')

		return
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
, **kwargs):
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
		If nothing found then returns exception.
		kwargs - additional arguments for http_req.
	'''
	if source[:4].lower().startswith('http'):
		status, j = safe(http_req)(url=source, **kwargs)
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
, **kwargs):
	'''	Downloads a XML document from the specified URL and gets the value
		by the list with 'map' of parent elements like ['foo', 'bar']
		
		element - XPath or list of XPath's.
		Example: element='/result/array/msgContact[1]/msgCtnt'

		kwargs - additional arguments for http_req.
	'''
	if url.startswith('http'):
		status, content = http_req(url=url, **kwargs)
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

def net_url_decode(url:str, encoding:str='utf-8')->str:
	' Decodes URL '
	return urllib.parse.unquote(url, encoding=encoding)

def net_url_encode(url:str, encoding:str='utf-8')->str:
	' Encodes URL '
	return urllib.parse.quote(url, encoding=encoding)

def net_html_unescape(html_str:str)->str:
	'''
	Decodes HTML escaped symbols:
		
		"That&#039;s an example" -> "That's an example"

	'''
	return html.unescape(html_str)



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
, timeout:int=500)->bool:
	'''
	Scan TCP port.
	*timeout* - timeout in milliseconds.
	'''
	SUCCESS = 0
	sock = socket.socket()
	sock.settimeout(timeout/1000)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	connected = sock.connect_ex((host, port)) is SUCCESS
	sock.close()
	return connected

def http_req_status(url:str, method='HEAD')->int:
	return getattr(requests, method.lower())(url).status_code

if __name__ == '__main__':
	html = r'''
	<!doctype html>
	<script>
		function count(elem) {
			// elem.classList.remove('flash')
			score_sound.play()
		}
	</script>
	<style>
		.score {
			display: flex;
			/* background-color: #333; */
		}

		/* @media (orientation: landscape) {
			.controls { grid-template-columns: 1fr 1fr; }
		} */
	</style>
	<body>
		<div class='controls'>
			<div class='score left' onclick='count(this)'>25</div>
			<div class='score right' onclick='count(this)'>25</div>
		</div>
	</body>
	'''
	print(html_minify(html))
else:
	patch_import()
