import os
import time
import socket
import requests
import urllib
import lxml.html
import re
import html
import psutil
import tempfile
from hashlib import md5
from bs4 import BeautifulSoup
import json
import subprocess
import datetime
import random
import warnings
import threading
import ftplib
from typing import Iterator, Tuple, Union
import json2html
from .tools import dev_print, exc_text, time_sleep, tdebug \
, locale_set, safe, patch_import, time_diff \
, median, is_iter, str_indent
from .plugin_filesystem import var_lst_get, path_get, file_name, file_dir

_USER_AGENT = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'}
_SPEED_UNITS = {'gb': 1_073_741_824, 'mb': 1_048_576, 'kb': 1024, 'b': 1}
_PUB_SUF_LST = set()

def http_req(url:str, encoding:str='utf-8', session:bool=False
, cookies:dict=None, headers:dict=None
, http_method:str='get', json_data:str=None
, post_file:str=None, post_hash:bool=False
, post_form_data:dict=None, post_file_capt:str='file'
, timeout:int=3, attempts:int=3, **kwargs)->str:
	'''
	Gets content of the specified URL
	
	**Kwargs tips:**
	
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
		args['files'] = {post_file_capt: file_obj}
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

def _rem_white(text:str)->str:
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
	return _rem_white(html)


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
		download to a temporary folder. If it is 'devnull'
		then do not write the file.

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
					tdebug(f'content-disposition error: {e}')
					fname = req.url.split('/')[-1]
				if fname:
					dst_file = os.path.join(dst_file, fname.strip('"'))
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

def html_clean(html_str:str, sep:str=' ', is_mail:bool=False
, del_spec:bool=True)->str:
	r'''
	Removes HTML tags from a string. Also removes content
	of non-text tags: *style, script, img*  
	*sep* - separator between tags.

		tass( html_clean('\r\n<a>t</a>\t'), 't')
		tass( html_clean('\r\n<a>t</a><a>t2</a>\t', sep='\n'), 't\nt2')
		tass( html_clean('\u200b\r \n<a>t</a>\t', is_mail=True), 't')
		tass( html_clean('<style>{}</style><a>t</a>\t'), 't')
		tass( html_clean('<img>jpg</img><a>t</a>\t', del_spec=False), 'jpg t')

	'''
	SPEC_CHARS = ' \r\n\t\u200b\xa0\u200c'
	DEL_TAGS = ('script', 'style', 'img')
	warnings.filterwarnings('ignore', category=UserWarning, module='bs4')
	soup = BeautifulSoup(html_str, 'html.parser')
	if del_spec:
		for tag in DEL_TAGS: [s.decompose() for s in soup(tag)]
	text = soup.get_text(separator=sep)
	if is_mail:
		text = text.strip(SPEC_CHARS)
	else:
		text = text.strip()
	if is_mail: text = ' '.join(text.split())
	return text

def html_element(url:str, element
, clean:bool=True, element_num:int=0
, attrib:str=None, **kwargs)->str:
	'''
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

	XPath cheatsheet: https://devhints.io/xpath  
	More XPath examples:
		'//div[@id="id"]/p'
		'//div[contains(@class, "main")]/div/script'
		'//table[2]/thead/tr/th[2]'
		'//ul[contains(@class, "pagination")]/li[1]/a/@href'

	'''
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
						_rem_white(e.get_text())
							for e in found_elem
					]
			else:
				if attrib:
					return [ e.get(attrib, None) for e in found_elem ]
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
					result.append( _rem_white(
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
					result.append( _rem_white(found_elem) )
				else:
					result.append(found_elem)
			else:
				if clean:
					result.append(
						_rem_white(found_elem.text_content())
					)
				else:
					result.append(
						lxml.etree.tostring(found_elem, encoding=str)
					)
	if len(element_li) == 1:
		return result[0]
	else:
		return result

def json_element(source:str, element:Union[list, tuple]=[]
, **kwargs)->Union[str, list]:
	'''
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
	*kwargs* - additional arguments for http_req.  
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
		status, content = safe(http_req)(url=url, **kwargs)
		if not status: raise content
	else:
		status = True
		content = url
	if isinstance(element, (list, tuple)):
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
	if isinstance(element, (list, tuple)):
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
	'''
	Get IP adresses of domain.
	'''
	data = socket.gethostbyname_ex(domain)
	return data[2]

def url_hostname(url:str, sld:bool=True)->str:
	'''
	Get hostname (domain name) from URL.

	*sld* - if True then return the second level domain
	otherwise return the full domain.

		tass( url_hostname('https://www.example.gov.uk'), 'example.gov.uk')
		tass( url_hostname('https://www.example.gov.uk', sld=False) \
		, 'www.example.gov.uk')
		tass( url_hostname('http://user:pwd@abc.example.com:443/api') \
		, 'example.com')
		tass( url_hostname('http://user:pwd@abc.example.com:443/api'
		, sld=False), 'abc.example.com')
		tass( url_hostname('http://user:pwd@192.168.0.1:80/api') \
		, '192.168.0.1')
		tass( url_hostname('http://abc.example.com:443/api?ip=1.2.3.4') \
		, 'example.com')

	'''
	global _PUB_SUF_LST
	if m := re.findall(r'\D(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[\:/]', url):
		return m[0]
	domain = urllib.parse.urlparse(url).netloc
	if '@' in domain: domain = domain.split('@')[1]
	if ':' in domain: domain = domain.split(':')[0]
	if not sld: return domain
	if not _PUB_SUF_LST:
		_PUB_SUF_LST = set(
			var_lst_get('_public_suffix_list')
		)
	variants = []
	for i in range(domain.count('.') + 1):
		variants.append( '.'.join(domain.split('.')[-(i+1):]) )
	for var in variants:
		if var in _PUB_SUF_LST: continue
		return var

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



def is_online(*sites, timeout:float=2.0)->int:
	r'''
	Checks if there is an internet connection using *HEAD*
	requests to the specified web sites.  
	The function will not raise an exception.  
	*timeout* - timeout in seconds.  

		tass( is_online(), 2 )
		tass( is_online('https://non.existent.domain'), 0 )

	'''
	if not sites:
		sites = (
			'https://www.google.com/'
			, 'https://yandex.ru/'
		)
	r = 0
	for site in sites:
		try:
			requests.head(site, timeout=timeout
				, headers={**_USER_AGENT})
			r += 1
		except:
			pass
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
	tdebug(date_str)
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
	r'''
	Returns just a status of HTTP request:

		tass( http_req_status('https://github.com'), 200)
		
	'''
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

def net_usage_str(interf:str)->Iterator[ Tuple[str] ]:
	'''
	Same as **net_usage** but in human readable format.
	**interf** - name of a network interface.
	Usage example:

		for up_down in net_usage_str('Local Area Connection'):
			print(up_down)
			time_sleep('1 sec')

	'''
	units = tuple(_SPEED_UNITS.keys())[::-1]
	
	def to_unit(val):
		for unit in units:
			if val < 1024.0: return f'{val:.1f} {unit}/s'
			val /= 1024.0

	for up_down in net_usage(interf):
		yield tuple(map(to_unit, up_down))

def ping_tcp(host:str, port:int, count:int=1, pause:int=100
, timeout:int=500)->tuple:
	'''
	Measure loss and response time with a TCP connection.
	Returns (True, (loss percentage, time in ms) )
	or (False, 'error text').  
	*pause* - pause in milliseconds between attempts  
	*timeout* - waiting time for a response in milliseconds.  

	Examples:

		tass( ping_tcp('8.8.8.8', 443)[1][1] > 10, True )
		tass( ping_tcp('127.0.0.1', 445)[1][1] < 15, True )
		tass( ping_tcp('non.existent.domain', 80), (False, '[Errno 11004] getaddrinfo failed') )

	'''
	timings = []
	last_err = 'OK'
	try:
		ip = random.choice( domain_ip(host) )
	except Exception as e:
		return False, str(e)
	full_start = datetime.datetime.now()
	for _ in range(count):
		with socket.socket( socket.AF_INET, socket.SOCK_STREAM ) as soc:
			soc.settimeout(timeout/1000)
			tstart = datetime.datetime.now()
			try:
				soc.connect((ip, port))
				timings.append(time_diff(tstart, unit='ms'))
				soc.shutdown(socket.SHUT_RD)
			except Exception as e:
				last_err = str(e)
				tdebug(last_err)
		time.sleep(pause / 1000)
	tdebug(ip, timings)
	tdebug('full time', time_diff(full_start, unit='ms'))
	if timings:
		perc = int( (count - len(timings)) / count * 100 )
		return True, ( perc, int(median(timings)))
	else:
		return False, last_err

def ping_icmp(host:str, count:int=3
, timeout:int=500, encoding:str='cp866')->tuple:
	'''
	Wrapper over ping.exe
	Returns (True, (loss %, aver. time) )
	or (False, 'cause of failure')
	
	Examples:
	
		tass( ping_icmp('8.8.8.8', 1)[0], True)
		tass( ping_icmp('non.existent.domain', 1), (False, 'host unreachable (1)') )
		tass( ping_icmp('127.0.0.1', 1), (True, (0, 0)) )

	'''
	proc = subprocess.Popen(
		('ping', '-n', str(count), '-w', str(timeout), host)
		, stderr=subprocess.STDOUT
		, stdout=subprocess.PIPE
		, encoding=encoding
	)
	out, ret = proc.communicate()[0], proc.returncode
	tdebug(ret, str_indent(out))
	if ret == 1: return False, 'host unreachable (1)'
	loss = re.findall(r'\((\d+)%', out)
	if not re.findall(r' \d+\.\d+\.\d+\.\d+: .+?=\d+\D+[<=]\d+\D+=\d+', out):
		return False, 'host unreachable (2)'
	loss = int(loss[0])
	av_time = int(
		re.findall(r' = (\d+).+? = (\d+).+? = (\d+)', out)[1][2]
	)
	return True, (loss, av_time)

def ftp_upload(fullpath, server:str
, user:str, pwd:str, dst_dir:str='/', port:int=21
, active:bool=True, debug_lvl:int=0, attempts:int=3
, timeout:int=10, secure:bool=False, encoding:str='utf-8')->tuple:
	'''
	Uploads file(s) to an FTP server
	Returns (True, None) or (False, ('error1', 'error2'...))

	*debug_lvl* - set to 1 to see the commands.
	
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
				features = tuple(
					f.strip() for f in ftp.sendcmd('FEAT').splitlines()
				)
				if 'UTF8' in features:
					ftp.sendcmd('CLNT Python')
					ftp.sendcmd('OPTS UTF8 ON')
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
	except Exception as e:
		errors.append(
			f'general error at line {e.__traceback__.tb_lineno}: '
			+ repr(e)
		)
	return len(errors) == 0, errors
	

	