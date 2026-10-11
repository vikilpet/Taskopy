r'''
Naming convention:  
*host* - host name or IP number.  
*hostname* - host name.  
'''
import os
import time
import socket
import requests
from requests.auth import HTTPBasicAuth
import urllib
import lxml.html
import re
import html
import psutil
import tempfile
import win32file
import unicodedata
import struct
from io import BytesIO
from hashlib import md5
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import json
import subprocess
import datetime
import random
import warnings
import threading
import functools
import ftplib
from typing import Iterator, Tuple, Union
import json2html
import idna
from .tools import dev_print, exc_text, tdebug \
, locale_set, safe, patch_import, re_replace \
, median, is_iter, str_indent, is_con, qprint, str_remove_white \
, value_to_unit, task_add, msg_warn, Callable, cache
from .plugin_filesystem import var_lst_get, path_get, file_name, file_dir
from .plugin_process import proc_wait


_USER_AGENT = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36'}
_SPEED_UNITS = {'gb': 1_073_741_824, 'mb': 1_048_576, 'kb': 1024, 'b': 1}
LAN_DOMAINS = ('lan', 'local', 'home')
_RE_PING_LOSS = re.compile(r'\((\d+)%')
_RE_PING_FAIL = re.compile(r' \d+\.\d+\.\d+\.\d+: .+?=\d+\D+[<=]\d+\D+=\d+')
_RE_PING_TIME = re.compile(r' = (\d+).+? = (\d+).+? = (\d+)')
_RE_HOST_IP = re.compile(r'\D(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[\:/]')
_ZW_TABLE = str.maketrans('', '',
	'\u200b'   # ZERO WIDTH SPACE
	'\u200c'   # ZERO WIDTH NON-JOINER
	'\u200d'   # ZERO WIDTH JOINER
	'\u2060'   # WORD JOINER
	'\ufeff'   # ZERO WIDTH NO-BREAK SPACE (BOM/ZWNBSP)
	'\u034f'   # COMBINING GRAPHEME JOINER — spam filler
	'\u200e'   # LEFT-TO-RIGHT MARK
	'\u200f'   # RIGHT-TO-LEFT MARK
	'\u202a'   # LEFT-TO-RIGHT EMBEDDING
	'\u202b'   # RIGHT-TO-LEFT EMBEDDING
	'\u202c'   # POP DIRECTIONAL FORMATTING
	'\u202d'   # LEFT-TO-RIGHT OVERRIDE
	'\u202e'   # RIGHT-TO-LEFT OVERRIDE — famous malware trick
	'\u2066'   # LEFT-TO-RIGHT ISOLATE
	'\u2067'   # RIGHT-TO-LEFT ISOLATE
	'\u2068'   # FIRST STRONG ISOLATE
	'\u2069'   # POP DIRECTIONAL ISOLATE
	'\u2061'   # FUNCTION APPLICATION
	'\u2062'   # INVISIBLE TIMES
	'\u2063'   # INVISIBLE SEPARATOR
	'\u2064'   # INVISIBLE PLUS
	'\u206a'   # INHIBIT SYMMETRIC SWAPPING
	'\u206b'   # ACTIVATE SYMMETRIC SWAPPING
	'\u206c'   # INHIBIT ARABIC FORM SHAPING
	'\u206d'   # ACTIVATE ARABIC FORM SHAPING
	'\u206e'   # NATIONAL DIGIT SHAPES
	'\u206f'   # NOMINAL DIGIT SHAPES
	'\ufff9'   # INTERLINEAR ANNOTATION ANCHOR
	'\ufffa'   # INTERLINEAR ANNOTATION SEPARATOR
	'\ufffb'   # INTERLINEAR ANNOTATION TERMINATOR
	'\u00A0'   # NO-BREAK SPACE
	'\u2800'   # BRAILLE PATTERN BLANK
	'\u0085'   # NEXT LINE (NEL)
	'\u180e'   # MONGOLIAN VOWEL SEPARATOR
	'\u2028'   # LINE SEPARATOR
	'\u2029'   # PARAGRAPH SEPARATOR
	'\u115f'   # HANGUL CHOSEONG FILLER
	'\u1160'   # HANGUL JUNGSEONG FILLER
	'\u3164'   # HANGUL FILLER
	'\uffa0'   # HALFWIDTH HANGUL FILLER
)
warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)
requests.packages.urllib3.disable_warnings(
	requests.packages.urllib3.exceptions.InsecureRequestWarning)

def http_req(url:str, encoding:str='utf-8'
, cookies:dict=None, headers:dict=None
, http_method:str='', post_json:dict|None=None
, post_file:str=None, post_hash:bool=False
, post_form_data:dict=None, post_file_capt:str=''
, timeout:float=3.0, attempts:int=3, auth:tuple=()
, as_json:bool=False, chunk_size:int=8192, **kwargs)->str|dict|Exception:
	r'''
	Gets content of the specified URL.  
	*post_file_capt* - if the file should be uploaded in
	browser default (multipart/form-data) way  
	
	**kwargs tips:**  
	Skip SSL verification: `verify=False`  
	Follow redirects: `allow_redirects=True`  
	Socks proxy: `proxies = {'https': 'socks5h://127.0.0.1:1080'}`  
	where *h* means to perform DNS queries via proxy  

	Caveats:

		- Header `If-Modified-Since` may result in zero file length.
		
	'''

	def file_stream():
		with open(post_file, 'rb') as f:
			while True:
				chunk = f.read(chunk_size)
				if not chunk:
					break
				yield chunk

	if not http_method:
		if (post_file or post_form_data or post_json):
			http_method = 'post'
		else:
			http_method = 'get'
	http_method = http_method.lower()
	args = {'url': url, 'json': post_json, 'timeout': timeout}
	if post_form_data: args['data'] = post_form_data
	if auth: args['auth'] = HTTPBasicAuth(*auth)
	file_obj = None
	post_file_hash = None
	stream_headers = {}
	if post_file:
		post_file = path_get(post_file)
		if post_hash: post_file_hash = _file_hash(post_file)
		if post_file_capt:
			file_obj = open(post_file, 'rb')
			args['files'] = {post_file_capt: file_obj}
		else:
			file_size = win32file.GetFileAttributesEx(post_file)[-1]
			fname = os.path.basename(post_file)
			fname2 = urllib.parse.quote(fname, safe='')
			if not all(ord(ch) < 128 for ch in fname):
				fname = fname2
			stream_headers = {
				'Content-Type': 'application/octet-stream'
				, 'Content-Disposition': f'attachment; filename="{fname}"'
					+ f'; filename*=UTF-8\'\'{fname2}'
				, 'Content-Length': str(file_size)
			}
			args['data'] = file_stream()
	else:
		post_file_hash = False
	req_obj = requests
	if cookies: args['cookies'] = cookies
	args['headers'] = {**_USER_AGENT, **stream_headers}
	if post_file_hash:
		args['headers']['Content-MD5'] = post_file_hash
	if headers: args['headers'].update(headers)
	for attempt in range(attempts):
		try:
			time.sleep(attempt)
			resp = getattr(req_obj, http_method)(**args, **kwargs)
			if resp.status_code >= 500:
				continue
			elif resp.status_code in (403, 404):
				break
			else:
				break
		except Exception as err:
			if isinstance(err, requests.exceptions.SSLError):
				return err
			if isinstance(err, requests.exceptions.InvalidHeader):
				return err
			if isinstance(err, TypeError):
				return err
			if is_con():
				qprint(f'failed again ({attempt}).'
					+ f' Error: {repr(err)}\nurl={url}')
	else:
		raise Exception(
			f'no more attempts ({attempts}), host={url_hostname(url)}'
		)
	if file_obj: file_obj.close()
	if as_json:
		content = resp.json()
	else:
		content = str(resp.content, encoding=encoding, errors='ignore')
	return content

def _rem_white(text:str)->str:
	r'''
	Removes an excessive white space from the string.
	'''
	if not text: return text
	return ' '.join(text.split())

def file_download(url:str, destination:str=None, attempts:int=3
, timeout:float|tuple[float|None,float|None]=3.0
, del_bad_file:bool=False, headers:dict={}
, size_limit:int=None, stop_event:threading.Event=None
, overwrite:bool=False
, chunk_size:int=1_048_576
, **kwargs)->str:
	r'''
	Download file from url to destination and return fullpath.  
	Returns a full path to the downloaded file.  
	
	*attempts* - how many times to retry download if failed.  
	*destination* - file, directory or None. If the latter,
	download to a temporary folder. If it is 'devnull'
	then do not write the file.  
	*overwrite* - overwrite file if exists.  
	*stop_event* - `threading` event to stop download.  
	*kwargs* - additional arguments for the `requests.get`  
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

	Caveats:

		- Header `If-Modified-Since` may result in zero file length.
		
	'''
	if isinstance(destination, (list, tuple)):
		destination = os.path.join(*destination)
		try:
			os.makedirs(os.path.dirname(destination))
		except FileExistsError:
			pass
	find_name:bool = False
	dst_file = destination
	if dst_file:
		find_name = os.path.isdir(dst_file)
		if not find_name:
			dst_file = path_get((
				file_dir(dst_file)
				, file_name(dst_file)
			))
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
					fname = req.url.split('/')[-1]
				if fname:
					dst_file = os.path.join(dst_file, fname.strip('"'))
					find_name = False
				else:
					with tempfile.TemporaryFile() as f:
						dst_file = f.name
			if os.path.isfile(dst_file) and not overwrite:
				return dst_file
			if dst_file == 'devnull':
				dst_file = os.devnull
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
				dev_print('could not delete a bad file: ' + str(e))
		last_exc.fullpath = dst_file
		raise last_exc
	return dst_file

def html_clean(html_str:str, sep:str=' ', strip_white:bool=True)->str:
	r'''
	Removes HTML tags from a string. Also removes content
	of non-text tags: *style, script, img*
	*sep* - separator between tags.
	*strip_white* - normalize whitespace (NFKC) but preserve new lines.

		asrt( html_clean('\r\n<a>t</a>\t'), 't')
		asrt( html_clean('\r\n<a>t</a><a>t2</a>\t', sep='\n'), 't\nt2')
		asrt( html_clean('\u200b\r \n<a>t</a>\t', strip_white=True), 't')
		asrt( html_clean('<style>{}</style><a>t</a>\t'), 't')
		asrt( bmark(html_clean, a=('<style>{}</style><a>t</a>\t',)), 300_000 )

	'''
	soup = BeautifulSoup(html_str, 'lxml')
	text = soup.get_text(separator=sep)
	soup.decompose()
	del soup
	text = unicodedata.normalize('NFKC', text).translate(_ZW_TABLE).strip()
	if strip_white:
		text = '\n'.join(
			' '.join(line.split()) for line in text.splitlines()
			if line.strip()
		)
	return text

def html_element(url:str, element
, clean:bool=True, element_num:int|str=0
, attrib:str='', tag_sep:str=' ', **kwargs)->str:
	r'''
	Get text of specified page element (div).
	Returns str or list of str.
	
	*url* - URL or string with HTML.  
	*attrib* - get specific attribute from element
	(TODO: not only for 'all').  
	*element* - dictionary (list of dictionaries)
	, or str (list of strings). If 'element' is a list
	then 'html_element' returns list of found elements.
	If it's a dict or list of dicts then method find_all
	of Beautiful Soup (BS) will be used.
	If it's a str or list of str then xpath will be used.  
	Example of dictionary for the BS:

			element={
				'name': 'span'
				, 'attrs': {'itemprop':'softwareVersion'}
			}

	XPath example:

			element='/html/body/div[1]/div/div'

	*clean* - remove html tags and spaces (Soup).  
	*kwargs* - additional arguments for http_req.  
	*element_num* - number of found element. If set
	to 'all' then returns all this elements.

	XPath cheatsheet: <https://devhints.io/xpath>  
	Element numbers start at 1.  
	More XPath examples:

		# by id
		'//div[@id="id"]/p'

		# by class:
		'//div[contains(@class, "main")]/div/script'

		# second element:
		'//table[2]/thead/tr/th[2]'

		# get tag attribute:
		'//ul[contains(@class, "pagination")]/li[1]/a/@href'

		# Get the tag containing the desired text and navigate to its sibling:
		//strong[contains(text(), "a text")]/following-sibling::strong[3]

		# Class name contains random suffix:
		//*[@class[starts-with(., "SomeClassName_")]]
	
	Note: *tbody* is often missing, but the browser automatically
	adds it.

	'''
	
	def clean_white(text)->str:
		return str_remove_white(text, algo='space')

	if not url[:4].lower().startswith('http'):
		html = url
	else:
		status, html = safe(http_req)(url=url, **kwargs)
		if not status: raise html
	if isinstance(element, (list, tuple)):
		element_li = element
	else:
		element_li = [element]
	result = []
	if isinstance(element_li[0], dict):
		parser = BeautifulSoup(html, 'lxml')
	elif element_li[0].startswith('/'):
		parser = lxml.html.fromstring(html
		, parser=lxml.html.HTMLParser(recover=True))
	else:
		parser = parser = BeautifulSoup(html, 'lxml')
	if element_num == 'all':
		found_elem = parser.find_all(**element)
		if found_elem:
			if clean:
				if attrib:
					return [e.get(attrib, None) for e in found_elem]
				else:
					return [clean_white(e.get_text()) for e in found_elem]
			else:
				if attrib:
					return [e.get(attrib, None) for e in found_elem]
				else:
					return list(map(str, found_elem))
		else:
			raise Exception('html_element: element not found')
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
					result.append( clean_white(
						found_elem[el_num].get_text()
					))
				else:
					result.append( str(found_elem[el_num]) )
			else:
				raise Exception('html_element: element not found')
			parser.decompose()
			del parser
		else:
			if len(element_li) == 1:
				el_num = element_num
			else:
				el_num = 0
			found_elem = parser.xpath(elem)[el_num]
			if isinstance(found_elem, str):
				if clean:
					result.append( clean_white(found_elem) )
				else:
					result.append(str(found_elem))
			else:
				if clean:
					result.append( tag_sep.join(
						clean_white(t) for t in found_elem.itertext()
						if not t.isspace()
					))
				else:
					result.append(
						lxml.etree.tostring(found_elem, encoding=str)
					)
	if len(element_li) == 1:
		return result[0]
	else:
		return result

def json_element(source:str, element:list|tuple=[]
, **kwargs)->str|list|tuple|float|int|dict:
	r'''
	Download JSON from URL and get its nested element by
	map of keys like ['list', 0, 'someitem', 1]  

	*source* - URL to download or string with JSON.  
	*element* - can be a None, list or list of lists so it will
	get every element specified in nested list and return
	list of values. If set to `None` - just return serialized JSON.  
	Examples:

		> element=['banks', 0, 'usd', 'sale']
		> 63.69
		
		> element=[
			['banks', 0, 'eur', 'sale']
			, ['banks', 0, 'usd', 'sale']
			, ['banks', 0, 'gbp', 'sale']
		]
		> result = [71.99, 63.69, 83.0]

	If nothing found then return exception.  
	*kwargs* - additional arguments for `http_req`  

	'''
	if source[:4].lower().startswith('http'):
		status, j = safe(http_req)(url=source, **kwargs)
		if not status: raise j
	else:
		j = source
	data = json.loads(j)
	if not element: return data
	if is_iter(element[0]):
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

def xml_element(url:str, elem:str
, elem_num:int=0, encoding:str='utf-8', remove_namespace:bool=False
, **kwargs):
	r'''
	Downloads a XML document from the specified URL and gets the value
	by the list with 'map' of parent elements like ['foo', 'bar']
	
	*elem* - XPath or list of XPath's.
	Example: elem='/result/array/msgContact[1]/msgCtnt'  
	*kwargs* - additional arguments for http_req.  
	'''
	if url.startswith('http'):
		status, content = safe(http_req)(url=url, **kwargs)
		if not status: raise content
	else:
		content = url
	if remove_namespace:
		content = re_replace(content, r'\sxmlns=".+?"', '')
	if isinstance(elem, (list, tuple)):
		elem_lst = elem
	else:
		elem_lst = [elem]
	result = []
	tree = lxml.etree.fromstring(content.encode(encoding=encoding))
	for elm in elem_lst:
		value = tree.xpath(elm)[elem_num]
		if value != None:
			result.append(value.text)
		else:
			raise Exception(f'xml_element: element not found: {elm}')
	if isinstance(elem, (list, tuple)):
		return result
	else:
		return result[0]

def net_host_ip(hostname:str)->list[str]:
	r'''
	Get IP adresses of a host name.  
	'''
	try:
		return socket.gethostbyname_ex(hostname)[2]
	except socket.gaierror:
		return []

domain_ip = net_host_ip

def net_pc_ip()->str:
	r'''
	Returns the main IP address of this computer.  

		asrt( bmark(net_pc_ip), 90_000 )

	'''
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.settimeout(0)
	try:
		sock.connect(('10.254.254.254', 1))
		ip = sock.getsockname()[0]
	except Exception:
		ip = '127.0.0.1'
	finally:
		sock.close()
	return ip

def net_ip_hostname(host:str)->str:
	r'''
	Reverse lookup IP -> host name. Returns empty string on fail.  
	*host* - IP or host name.  

		asrt( net_ip_hostname('8.8.8.8'), 'dns.google' )

	'''
	try:
		return socket.gethostbyaddr(host)[0]
	except socket.herror:
		return ''

@functools.cache
def net_pc_hostname()->str:
	r'''
	Returns the host name of the computer in lower case.

		asrt( bmark(net_pc_hostname), 500 )

	'''
	return socket.gethostname().lower()

def url_hostname(url:str, sld:bool=True)->str:
	r'''
	Returns the hostname (domain name) in lower case from a URL.

	*sld* - if set then returns the second level domain
	otherwise returns the full domain.

		asrt( url_hostname('https://www.example.gov.uk'), 'example.gov.uk')
		asrt( url_hostname('https://www.example.gov.uk', sld=False) \
		, 'www.example.gov.uk')
		asrt( url_hostname('http://user:pwd@abc.example.com:443/api') \
		, 'example.com')
		asrt( url_hostname('http://user:pwd@abc.example.com:443/api'
		, sld=False), 'abc.example.com')
		asrt( url_hostname('http://user:pwd@192.168.0.1:80/api') \
		, '192.168.0.1')
		asrt( url_hostname('http://abc.example.com:443/api?ip=1.2.3.4') \
		, 'example.com')
		asrt( url_hostname('http://server.lan:80/'), 'server.lan' )
		asrt( url_hostname('www.example.lan'), 'example.lan' )
		asrt( bmark(url_hostname, ('http://server.lan:80/',)), 65_000)
		asrt( bmark(url_hostname, ('https://www.example.gov.uk',)), 60_000)

	'''
	url = url.lower()
	if m := _RE_HOST_IP.findall(url): return m[0]
	if '://' in url:
		domain = urllib.parse.urlparse(url).netloc
	else:
		domain = url
	if '@' in domain: domain = domain.split('@')[1]
	if ':' in domain: domain = domain.split(':')[0]
	domain = idna.decode(domain, uts46=True)
	if not sld: return domain
	if not cache.public_suffix_list:
		cache.public_suffix_list = set( var_lst_get('_public_suffix_list') )
		cache.public_suffix_list.update(LAN_DOMAINS)
	variants = []
	for i in range(domain.count('.') + 1):
		variants.append( '.'.join(domain.split('.')[-(i+1):]) )
	for var in variants:
		if var in cache.public_suffix_list: continue
		return var
	return '<?>'

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



def net_is_online(
	sites:tuple|str=('http://clients3.google.com/generate_204', 'http://captive.apple.com/hotspot-detect.html')
	, timeout:float=2.0
)->int:
	r'''
	A simple check if there is an internet connection with *HEAD*
	requests to the specified sites.  
	The function will not raise any exception.  
	*timeout* - timeout in seconds.  

		asrt( is_online(), 2 )
		asrt( is_online( ('https://non.existent.domain',) ), 0 )

	'''
	if isinstance(sites, str):
		sites = (sites, )
	elif not isinstance(sites, (tuple, list)):
		raise TypeError(f'Incorrect data type of *sites*: {type(sites)}')
	result = 0
	for site in sites:
		try:
			resp = requests.head(
				site
				, timeout=timeout
				, headers={**_USER_AGENT}
				, allow_redirects=False
			)
			result += 1
		except Exception:
			pass
	return result

def net_is_online_socks5(
	proxy:str
	, sites:tuple|str=('http://clients3.google.com/generate_204', 'http://captive.apple.com/hotspot-detect.html')
	, timeout:float=2.0
)->int:
	r'''
	A simple check if there is an internet connection via a *SOCKS5*
	proxy with *HEAD* requests to the specified sites.
	The function will not raise any exception.
	Env vars (*HTTP_PROXY* etc.) are ignored — only *proxy* is used.  
	*proxy* - socks5 proxy URL, e.g. `'socks5h://127.0.0.1:9050'`.
	`socks5h://` resolves DNS through the proxy;
	`socks5://` resolves locally.  
	*timeout* - timeout in seconds.  

	'''
	if isinstance(sites, str):
		sites = (sites, )
	elif not isinstance(sites, (tuple, list)):
		raise TypeError(f'Incorrect data type of *sites*: {type(sites)}')

	_proxies = {'http': proxy, 'https': proxy}

	result = 0
	with requests.Session() as s:
		s.trust_env = False
		for site in sites:
			try:
				resp = s.head(
					site
					, timeout=timeout
					, headers={**_USER_AGENT}
					, proxies=_proxies
					, allow_redirects=False
				)
				result += 1
			except Exception:
				pass
	return result
def _file_hash(fullpath:str)->str:
	hash_md5 = md5()
	with open(fullpath, 'rb') as fi:
		for chunk in iter(lambda: fi.read(4096), b''):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()

def json_to_html(json_data, **kwargs)->str:
	''' Convert json to HTML table with
		module json2html '''
	return json2html.json2html.convert(
		json=json_data, **kwargs)

def http_header(url:str, header:str
, timeout:float=2.0, **kwargs)->str|dict:
	r'''
	Get HTTP header of URL or get them all (as a dictionary)
	if header=='all'. In the latter case, the case insensitive
	dictionary will return  
	'''
	headers={**_USER_AGENT, **kwargs.get('headers', {}) }
	req = requests.head(url, timeout=timeout
	, headers=headers, **kwargs)
	if header == 'all': return req.headers
	return req.headers.get(header)

def http_h_last_modified(url:str, header:str='Last-Modified', **kwargs):
	r'''
	HTTP Last Modified time in datetime format
	'''
	date_str = http_header(url, header=header, **kwargs)
	if is_con(): qprint(date_str)
	with locale_set('C'):
		return datetime.datetime.strptime(date_str
		, '%a, %d %b %Y %H:%M:%S GMT')

def _port_scan(host:str, port:int, timeout:int=500)->bool:
	r'''
	Scans a TCP port and returns `True` on success.  
	*timeout* - timeout in milliseconds.  
	'''
	SUCCESS = 0
	sock = socket.socket()
	sock.settimeout(timeout/1000)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	connected = sock.connect_ex((host, port)) is SUCCESS
	sock.close()
	return connected

def port_scan(host:str, port:int, timeout:int=500
, retry_num:int=2, retry_delay:int|str|float='100 ms')->bool:
	r'''
	Scans a TCP port and returns `True` on success.  
	*timeout* - timeout in milliseconds.  
	'''
	if isinstance(retry_delay, str):
		retry_delay = value_to_unit(retry_delay, 'second')
	for attempt in range(retry_num):
		if _port_scan(host=host, port=port, timeout=timeout): return True
		if attempt + 1 < retry_num: time.sleep(retry_delay)
	return False

net_port_scan = port_scan

def http_req_status(url:str, method='HEAD', timeout:float=1.0)->int:
	r'''
	Returns just a status of HTTP request:

		asrt( http_req_status('https://github.com', timeout=3.0), 200)
		
	'''
	return getattr(requests, method.lower())(url, timeout=timeout).status_code

if __name__ == '__main__':
	pass
else:
	patch_import()

def table_html(table:list, headers:bool=True
, empty_str:str='-', consider_empty:tuple=(None, '')
, table_class:str='')->str:
	'''
	Converts list of tuples/lists to a HTML table.
	List example:

		[
			('Name', 'Age'),
			('John', '27'),
			('Jane', '24'),
		]

	'''
	if table_class:
		html = f'<table class="{table_class}">'
	else:
		html = '<table>'
	if headers:
		html += '<thead>'
		for head in table.pop(0):
			html += f'<th>{head}</th>'
		html += '</thead>'
	html += '<tbody>'
	for row in table:
		html += '<tr>'
		for cell in row:
			if cell in consider_empty:
				html += f'<td>{empty_str}</td>'
			else:
				html += f'<td>{cell}</td>'
		html += '</tr>'
	html += '</tbody>'
	html += '</table>'
	return html

def net_usage(interf:str, unit='b')->Iterator[ Tuple[float] ]:
	'''
	Returns the current network usage (upload, download)
	in bits/sec. See also **net_usage_str**
	**interf** - name of a network interface.
	Usage example:

		for up_down in net_usage('LAN', unit='mb'):
			print(up_down)
			time_sleep('1 sec')

	'''
	prev_up, prev_down, prev_time = 0, 0, 0
	coef = 8 / _SPEED_UNITS.get(unit.lower())
	while True:
		cur_time = time.time()
		dtime = cur_time - prev_time
		cur_up, cur_down, *_ = psutil.net_io_counters(pernic=True)[interf]
		up_speed = (cur_up - prev_up) * coef / dtime
		down_speed = (cur_down - prev_down) * coef / dtime
		prev_up, prev_down, prev_time = cur_up, cur_down, cur_time
		yield up_speed, down_speed

def net_usage_str(interf:str, fract:bool=True
, time_suffix:str='/s')->Iterator[ Tuple[str] ]:
	r'''
	Same as **net_usage** but in human readable format.  
	*interf* - name of a network interface.  
	*fract* - with fractional part  
	Usage example:

		for up_down in net_usage_str('Local Area Connection'):
			print(up_down)
			time_sleep('1 sec')

	'''
	units = tuple(_SPEED_UNITS.keys())[::-1]
	
	def to_unit(val):
		for unit in units:
			if val < 1024.0:
				if fract:
					return f'{val:.1f} {unit}{time_suffix}'
				else:
					return f'{int(val)} {unit}{time_suffix}'
			val /= 1024.0

	for up_down in net_usage(interf):
		yield tuple(map(to_unit, up_down))

def ping_tcp(host:str, port:int, count:int=1, pause:int=100
, timeout:int=500)->tuple:
	r'''
	Measure loss and response time with a TCP connection.
	Returns (True, (loss percentage, time in ms) )
	or (False, 'error text').  
	*pause* - pause in milliseconds between attempts  
	*timeout* - waiting time for a response in milliseconds.  

	Examples:

		asrt( ping_tcp('8.8.8.8', 443)[1][1] > 10, True )
		asrt( ping_tcp('127.0.0.1', 445)[1][1] < 15, True )
		asrt( ping_tcp('non.existent.domain', 80), (False, 'Cannot choose from an empty sequence') )

	'''
	timings = []
	last_err = 'OK'
	try:
		ip = random.choice( net_host_ip(host) )
	except Exception as err:
		return False, str(err)
	full_start = time.perf_counter_ns()
	for _ in range(count):
		with socket.socket( socket.AF_INET, socket.SOCK_STREAM ) as sock:
			sock.settimeout(timeout/1000)
			tstart = time.perf_counter_ns()
			try:
				sock.connect((ip, port))
				timings.append(
					(time.perf_counter_ns() - tstart) // 1_000_000
				)
				sock.shutdown(socket.SHUT_RD)
			except Exception as e:
				last_err = str(e)
				tdebug(last_err)
		time.sleep(pause / 1000)
	full_time = (time.perf_counter_ns() - full_start) // 1_000_000
	tdebug(f'{ip=}, {full_time=}, {timings=}')
	if not timings: return False, last_err
	loss = (count - len(timings)) * 100 // count
	return True, ( loss, int(median(timings)))

def ping_icmp(host:str, count:int=3
, timeout:int=500, encoding:str='cp866')->tuple[bool, tuple|str]:
	r'''
	Wrapper over ping.exe.
	Returns (True, (loss percentage, time in ms) )
	or (False, 'cause of failure').  
	
	Examples:
	
		asrt( ping_icmp('8.8.8.8', 1)[0], True)
		asrt( ping_icmp('non.existent.domain', 1), (False, 'host unreachable (1)') )
		asrt( ping_icmp('127.0.0.1', 1), (True, (0, 0)) )

	'''
	ret, out, err = proc_wait(f'ping -n {count} -w {timeout} {host}'
	, encoding=encoding)
	if ret == 1: return False, 'host unreachable (1)'
	loss = _RE_PING_LOSS.findall(out)
	if not _RE_PING_FAIL.findall(out):
		return False, 'host unreachable (2)'
	loss = int(loss[0])
	av_time:int = 0
	av_time = int( _RE_PING_TIME.findall(out)[1][2] )
	return True, (loss, av_time)
def _socks5_handshake(tcp_sock, username=None, password=None):
	'''SOCKS5 method negotiation + optional auth.'''
	if username:
		tcp_sock.sendall(b'\x05\x02\x00\x02')
	else:
		tcp_sock.sendall(b'\x05\x01\x00')
	response = tcp_sock.recv(2)
	if len(response) < 2:
		raise ConnectionError('SOCKS5 greeting failed')
	method = response[1]
	if method == 0x00:
		return
	elif method == 0x02 and username:
		auth = (b'\x01'
			+ bytes([len(username)]) + username.encode()
			+ bytes([len(password)]) + password.encode())
		tcp_sock.sendall(auth)
		response = tcp_sock.recv(2)
		if response[1] != 0:
			raise ConnectionError('SOCKS5 auth failed')
	else:
		raise ConnectionError(f'SOCKS5 method {method} not supported')

def _socks5_udp_associate(tcp_sock):
	'''Send UDP ASSOCIATE, return (relay_addr, relay_port).'''
	tcp_sock.sendall(b'\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00')
	response = b''
	while len(response) < 10:
		chunk = tcp_sock.recv(256)
		if not chunk:
			raise ConnectionError('SOCKS5 closed during UDP ASSOCIATE')
		response += chunk
	reply_code = response[1]
	if reply_code != 0:
		errors = {1: 'general failure', 2: 'not allowed',
			3: 'network unreachable', 4: 'host unreachable',
			5: 'connection refused', 6: 'TTL expired',
			7: 'command not supported',
			8: 'address type not supported'}
		raise ConnectionError(
			f'UDP ASSOCIATE rejected: {errors.get(reply_code, "unknown")}')
	atyp = response[3]
	offset = 4
	if atyp == 1:
		addr = socket.inet_ntoa(response[offset:offset+4])
		offset += 4
	elif atyp == 3:
		dlen = response[offset]
		addr = response[offset+1:offset+1+dlen].decode()
		offset += 1 + dlen
	elif atyp == 4:
		addr = socket.inet_ntop(socket.AF_INET6, response[offset:offset+16])
		offset += 16
	else:
		raise ConnectionError(f'Unknown ATYP {atyp}')
	port = struct.unpack('>H', response[offset:offset+2])[0]
	return addr, port

def _socks5_udp_wrap(dst_host, dst_port, payload):
	'''Wrap payload in SOCKS5 UDP header.'''
	try:
		ip = socket.inet_aton(dst_host)
		return b'\x00\x00\x00\x01' + ip + struct.pack('>H', dst_port) + payload
	except OSError:
		return (b'\x00\x00\x00\x03' + bytes([len(dst_host)])
			+ dst_host.encode() + struct.pack('>H', dst_port) + payload)

def _parse_socks5_udp_header(data):
	'''Parse SOCKS5 UDP relay header. Returns (src_addr, src_port, payload).'''
	if len(data) < 6:
		return None, None, data
	atyp = data[3]
	offset = 4
	if atyp == 1:
		if len(data) < offset + 4 + 2:
			return None, None, data
		addr = socket.inet_ntoa(data[offset:offset+4])
		offset += 4
	elif atyp == 3:
		if len(data) < offset + 1:
			return None, None, data
		dlen = data[offset]
		addr = data[offset+1:offset+1+dlen].decode()
		offset += 1 + dlen
	elif atyp == 4:
		if len(data) < offset + 16 + 2:
			return None, None, data
		addr = socket.inet_ntop(socket.AF_INET6, data[offset:offset+16])
		offset += 16
	else:
		return None, None, data
	port = struct.unpack('>H', data[offset:offset+2])[0]
	offset += 2
	return addr, port, data[offset:]

STUN_MAGIC_COOKIE = 0x2112A442

def _stun_binding_request(txid: bytes) -> bytes:
	'''Build a 20-byte STUN Binding Request.'''
	return struct.pack('>HHI', 0x0001, 0, STUN_MAGIC_COOKIE) + txid

def _stun_validate_response(data: bytes, expected_txid: bytes) -> bool:
	'''Check if response is a valid STUN Binding Success Response with matching TXID.'''
	if len(data) < 20:
		return False
	msg_type, msg_len, cookie = struct.unpack('>HHI', data[:8])
	txid = data[8:20]
	if msg_type != 0x0101:
		return False
	if cookie != STUN_MAGIC_COOKIE:
		return False
	return txid == expected_txid

def ping_stun_socks5(
	socks_host:str
	, socks_port:int
	, dst_host:str='stun.l.google.com'
	, dst_port:int=19302
	, socks_user:str|None=None
	, socks_pass:str|None=None
	, count:int=4
	, pause:int=100
	, timeout:int=2000
)->tuple:
	r'''
	Measure loss and response time with a STUN Binding Request
	sent through SOCKS5 UDP ASSOCIATE.

	Returns (True, (loss percentage, time in ms) )
	or (False, 'error text').
	*pause* - pause in milliseconds between attempts
	*timeout* - waiting time for a response in milliseconds.
	NOTE: the first packet time is discarded, you better
	set *count* to 2 or more.  

	Public STUN servers:

		stun.l.google.com:19302       Google
		stun1.l.google.com:19302      Google
		stun2.l.google.com:19302      Google
		stun3.l.google.com:19302      Google
		stun4.l.google.com:19302      Google
		stun.cloudflare.com:3478      Cloudflare
		stun.miwifi.com:3478          Xiaomi
		stun.syncthing.net:3478       Syncthing
		stun.nextcloud.com:3478       Nextcloud
		stun.sipgate.net:3478         Sipgate
		stun.ekiga.net:3478           Ekiga
		stun.internetcalls.com:3478   Internetcalls
		stun.voipbuster.com:3478      Voipbuster
		stun.antisip.com:3478         Antisip
		stun.bluesip.net:3478         Bluesip
		stun.dus.net:3478             Dus.net
		stun.gmx.net:3478             GMX
		stun.schlund.de:3478          Schlund
		stun.1und1.de:3478            1&1
		stun.halonet.net:3478         Halonet

	Examples:

		asrt( ping_stun_socks5('10.0.1.3', 20170)[0], True )
		asrt( ping_stun_socks5('10.0.1.3', 20170)[1][1] > 10, True )
		asrt( ping_stun_socks5('10.0.1.3', 20170, 'stun.cloudflare.com', 3478)[0], True )

	'''
	timings = []
	last_err = 'OK'
	udp_sock = None
	tcp_sock = None
	try:
		tcp_sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
		tcp_sock.settimeout(timeout/1000)
		tcp_sock.connect((socks_host, socks_port))
		_socks5_handshake(tcp_sock, socks_user, socks_pass)
		relay_addr, relay_port = _socks5_udp_associate(tcp_sock)
		if relay_addr in ('0.0.0.0', '::'):
			relay_addr = socks_host
		relay = (relay_addr, relay_port)

		udp_sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		udp_sock.settimeout(timeout/1000)

		for _ in range(count):
			try:
				txid = os.urandom(12)
				stun_req = _stun_binding_request(txid)
				packet = _socks5_udp_wrap(dst_host, dst_port, stun_req)

				tstart = time.perf_counter_ns()
				udp_sock.sendto(packet, relay)
				data, _ = udp_sock.recvfrom(2048)

				_, _, payload = _parse_socks5_udp_header(data)
				if not _stun_validate_response(payload, txid):
					raise ValueError('invalid STUN response')

				timings.append(
					(time.perf_counter_ns() - tstart) // 1_000_000
				)
			except Exception as err:
				last_err = str(err)
			time.sleep(pause / 1000)

	except Exception as err:
		last_err = str(err)
	finally:
		for sock in (udp_sock, tcp_sock):
			if sock:
				try: sock.close()
				except: pass

	tdebug(timings)
	if not timings: return False, last_err
	steady = timings[1:] if len(timings) > 1 else timings
	loss = (count - len(timings)) * 100 // count
	return True, ( loss, int(median(steady)) )

def ftp_upload(fullpath:str|list|tuple, server:str
, user:str, pwd:str, dst_dir:str='/', port:int=21
, active:bool=True, debug_lvl:int=0, attempts:int=3
, timeout:int=10, secure:bool=False, encoding:str='utf-8')->tuple[bool, list]:
	r'''
	Uploads file(s) to an FTP server.  
	Returns (True, []) or (False, ['error1', 'error2'...])  
 
	*debug_lvl* - set to 1 to see the commands.  
	*timeout* - time in seconds or string like '10 sec'  
	
	Error 'EOF occurred in violation of protocol' - self signed
	certificate of server?

	'''
	SLEEP_MULT = 5
	if isinstance(fullpath, str):
		files = (fullpath, )
	elif is_iter(fullpath):
		files = tuple(fullpath)
	else:
		raise Exception('unknown type of fullpath')
	if isinstance(timeout, str):
		timeout = value_to_unit(timeout, 'second')
	errors = []
	ftpclass = ftplib.FTP_TLS if secure else ftplib.FTP
	try:
		with ftpclass() as ftp:
			ftp.set_debuglevel(debug_lvl)
			ftp.connect(host=server, port=port, timeout=timeout)
			ftp.login(user=user, passwd=pwd)
			if secure: ftp.prot_p()
			ftp.set_pasv(not active)
			if encoding: ftp.encoding = encoding
			if encoding == 'utf-8':
				try:
					feat_str = ftp.sendcmd('FEAT')
				except ftplib.error_perm:
					pass
				else:
					features = tuple( f.strip() for f in feat_str.splitlines() )
					if 'UTF8' in features:
						try:
							ftp.sendcmd('CLNT Python')
							ftp.sendcmd('OPTS UTF8 ON')
						except ftplib.error_perm:
							pass
			if dst_dir != '/': ftp.cwd(dst_dir)
			for fpath in files:
				for att in range(attempts):
					time.sleep(att * SLEEP_MULT)
					basename = os.path.basename(fpath)
					try:
						with open(fpath, 'br') as fd:
							ftp.storbinary(
								cmd='STOR ' + basename
								, fp=fd
							)
					except OSError as e:
						if e.errno != 0:
							errors.append(f'ftp.storbinary OSError: {repr(e)}')
					except Exception as e:
						errors.append(f'ftp.storbinary exception: {repr(e)}')
					ftp.size(basename)
					ftp_size = ftp.size(basename)
					loc_size = os.stat(fpath).st_size
					if ftp_size != None:
						if ftp_size == loc_size:
							break
						else:
							errors.append('file sizes do not match:'
							+ f' local={loc_size} vs ftp={ftp_size}')
				else:
					errors.append(f'no more attempts')
	except:
		errors.append(exc_text())
	return len(errors) == 0, errors

import ftplib

def ftp_dir_list(
	host: str,
	username: str,
	password: str,
	folder: str,
	port: int = 21,
	timeout: int = 30
) -> tuple[bool, list[str] | str]:
	r'''
	Connects to an FTP server and retrieves a listing of files and directories in 'folder'.
	Returns (True, [...]) on success, or (False, "error message") on failure.
	'''
	try:
		ftp = ftplib.FTP()
		ftp.connect(host, port, timeout)
		ftp.login(username, password)
		ftp.cwd(folder)

		try:
			listing: list[str] = [
				name + ("/" if facts.get("type") == "dir" else "")
				for name, facts in ftp.mlsd()
			]
		except (ftplib.error_perm, AttributeError):
			listing = ftp.nlst()

		ftp.quit()
		return True, listing

	except ftplib.all_errors as err:
		return False, f"FTP error: {err}"

def ftp_dir_list_time(
	host: str,
	username: str,
	password: str,
	folder: str,
	port: int = 21,
	timeout: int = 30,
	debug: bool = False
) -> tuple[bool, list[tuple[str, datetime.datetime]] | str]:
	r'''
	Connects to an FTP server and retrieves a list
	of (filename, modification datetime).  
	If `debug=True`, prints command/response traces.  
	Returns (True, entries) on success or (False, error_message) on failure.  
	'''
	log_lines: list[str] = []
	entries: dict[str, datetime.datetime] = {}

	def log(cmd: str, resp: str) -> None:
		log_lines.append(f"> {cmd}\n< {resp}")

	try:
		ftp = ftplib.FTP()
		resp = ftp.connect(host, port, timeout)
		log(f"CONNECT {host}:{port}", resp or "connected")

		resp = ftp.login(username, password)
		log(f"LOGIN {username}/****", resp)

		resp = ftp.cwd(folder)
		log(f"CWD {folder}", resp)
		try:
			resp = ftp.sendcmd("FEAT")
			log("FEAT", resp)
		except Exception as e:
			log("FEAT", f"error: {e}")
		raw: list[str] = []
		try:
			ftp.retrlines("MLSD", raw.append)
			log("MLSD", "\n".join(raw))
			for line in raw:
				parts = line.split(" ", 1)
				facts_part = parts[0]
				name = parts[1] if len(parts) > 1 else ""
				facts = {}
				for item in facts_part.rstrip(";").split(";"):
					if "=" in item:
						k, v = item.split("=", 1)
						facts[k] = v
				mod = facts.get("modify")
				if mod:
					ts = datetime.datetime.strptime(mod, "%Y%m%d%H%M%S")
					entries[name] = ts
		except Exception as e:
			log("MLSD", f"error: {e}")
		try:
			names = ftp.nlst()
			log("NLST", ", ".join(names))
		except Exception as e:
			log("NLST", f"error: {e}")
			ftp.quit()
			log("QUIT", "connection closed")
			if debug:
				qprint("\n".join(log_lines))
			return False, f"Cannot list names: {e}"
		for name in names:
			if name in entries:
				continue
			try:
				resp = ftp.sendcmd(f"MDTM {name}")
				log(f"MDTM {name}", resp)
				_, mod = resp.split()
				ts = datetime.datetime.strptime(mod, "%Y%m%d%H%M%S")
				entries[name] = ts
			except Exception as e:
				log(f"MDTM {name}", f"error: {e}")

		ftp.quit()
		log("QUIT", "connection closed")

		if debug:
			qprint("\n".join(log_lines))

		if entries:
			result = list(entries.items())
			return True, result
		else:
			return False, "No timestamps retrieved via MLSD or MDTM."

	except ftplib.all_errors as e:
		log("ERROR", str(e))
		if debug:
			qprint("\n".join(log_lines))
		return False, f"FTP error: {e}"

def net_speedtest(url:str)->float:
	r'''
	Download the file without saving to disk and measure
	the average download speed.  
	'''
	chunk_size = 1024 * 1024  # 1 MB per chunk
	speed_measurements = []
	total_bytes_dload = 0
	with requests.get(url, stream=True) as response:
		response.raise_for_status()
		buffer = BytesIO()
		for chunk in response.iter_content(chunk_size=chunk_size):
			start_time = time.perf_counter_ns()
			buffer.write(chunk)
			end_time = time.perf_counter_ns()
			total_bytes_dload += len(chunk)
			dload_time_sec = (end_time - start_time) / 1e9
			speed_mbps = (len(chunk) * 8) / (dload_time_sec * 1e6)
			if is_con():
				qprint(f"Downloaded 1 MB in {dload_time_sec:.3f} seconds. Speed: {speed_mbps:.3f} Mbit/s")
			speed_measurements.append(speed_mbps)
	if is_con():
		qprint(f'{total_bytes_dload=}, {speed_measurements=}')
	return median(speed_measurements)

def task_add_if(pc_name:str|set[str]|tuple[str]=''
, rule:Callable|list[Callable]|None=None):
	r'''
	Conditionally adds an attribute indicating that the function is a *task*.  
	*pc_name* — checks the name of this PC (case insensitive).  
	'''
	if (not pc_name) and (not rule):
		msg_warn(f'No *task_add_if* arguments are specified')
		return lambda f: f
	if rule is None:
		rule = []
	elif isinstance(rule, Callable):
		rule = [rule]
	else:
		msg_warn(f'Wrong type of *rule* in *task_add_if*: {type(rule)}')
		return lambda f: f
	if pc_name:
		hostname = net_pc_hostname()
		if isinstance(pc_name, str):
			pc_name = {pc_name.lower(), }
		else:
			pc_name = set(p.lower() for p in pc_name)
		rule.append(lambda: hostname in pc_name)
	passed:bool = True
	for func in rule:
		try:
			if not func():
				passed = False
				break
		except:
			passed = False
			msg_warn('Rule validation exception in *task_add_if*', 'task_add_if')
	return task_add if passed else lambda f: f
