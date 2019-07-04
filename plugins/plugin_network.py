﻿import os
import requests
import urllib
import tempfile
from bs4 import BeautifulSoup
import json

def page_get(url:str, encoding:str='utf-8')->str:
	''' Get content of the specified url
	'''
	try:
		req = requests.get(url)
	except Exception as e:
		return 'error: download failed'
	if req.status_code == 200:
		return str(req.content, encoding=encoding, errors='ignore')
	else:
		return f'error: status {req.status_code}'

def file_download(url:str, destination:str=None)->str:
	''' Download file from url to destination and return fullpath.
		If destination is a folder, then get filename from url
		If destination is None then download to temporary file
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
	r = dest.name
	dest.close()
	urllib.request.urlretrieve (url, r)
	return r

def html_element_get(url:str, find_all_args
					, clean:bool=True , encoding:str='utf-8'
					, session:bool=False, headers:dict=None)->str:
	''' Get text of specified page element (div).
		find_all_args - dict that will passed to find_all method
			https://www.crummy.com/software/BeautifulSoup/bs4/doc/
			It can be a list of dicts.
			Example:
				find_all_args={
					'name': 'span'
					, 'attrs': {'itemprop':'softwareVersion'}
				}
		Returns only the first occurrence.
		clean - remove html tags and spaces
		headers - optional dictionary with request headers
		session - use requests.Session instead of get
		cookies - dictionary with cookies like {'GUEST_LANGUAGE_ID': 'ru_RU'}
	'''
	if session:
		ses = requests.Session()
		ses.headers.update(headers)
		ses.cookies.update(cookies)
		req = ses.get(url)
	else:
		req = requests.get(url, headers=headers)
	if req.status_code != 200:
		return f'error {req.status_code}'
	html = str(req.content, encoding=encoding
				, errors='ignore')
	soup = BeautifulSoup(html, 'html.parser')
	if type(find_all_args) is list:
		r = []
		for d in find_all_args:
			r += soup.find_all(**d)
		if r:
			if clean:
				print(r)
				r = [i.get_text() for i in r]
				r = ' '.join(r)
				return r
			else:
				return r
		else:
			return 'not found'
	else:
		r = soup.find_all(**find_all_args)
		if r:
			if clean:
				return r[0].get_text()
			else:
				return r[0]
		else:
			return 'not found'

def json_element_get(url:str, element:list, headers:dict=None
					, session:bool=False, cookies:dict=None):
	''' Download json by url and get its nested element by
			map of keys like ['list', 0, 'someitem', 0]
		element - can be a list or list of lists so it will
			get every element specified in nested list and return
			list of values.
			examples:
				element=['banks',0,'usd','sale']
					result: 63.69
				
				element=[
					['banks',0,'eur','sale']
					,['banks',0,'usd','sale']
					,['banks',0,'gbp','sale']
				]
					result = [71.99, 63.69, 83.0]
		If nothing found then return 'not found'
		headers - optional dictionary with request headers
		session - use requests.Session instead of get
		cookies - dictionary with cookies like {'GUEST_LANGUAGE_ID': 'ru_RU'}
	'''
	if session:
		ses = requests.Session()
		ses.headers.update(headers)
		ses.cookies.update(cookies)
		req = ses.get(url)
	else:
		req = requests.get(url, headers=headers)
	if req.status_code == 200:
		j = req.content
	else:
		if type(element[0]) is list:
			return [f'error {req.status_code}']
		else:
			return f'error {req.status_code}'
	data = json.loads(j)
	if type(element[0]) is list:
		li = []
		for elem in element:
			da = data
			for key in elem: da = da[key]
			li.append(da)
		r = li
	else:
		for key in element: data = data[key]
		r = data
	return r

def tracking_status_rp(track_number:str)->str:
	''' Get last status of Russian post parcel 
	'''
	url = r'https://www.pochta.ru/tracking?p_p_id=trackingPortlet_WAR_portalportlet&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=getList&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_pos=1&p_p_col_count=2&barcodeList={}&pos'
	status_list = json_element_get(
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
		, headers={
			'Accept-Language':'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
		}
	)
	return ', '.join(status_list)