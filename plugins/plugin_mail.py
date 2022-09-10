
import smtplib
import ssl
import glob
import os
import time
import datetime
from typing import Callable, Tuple, List
from email.message import EmailMessage, Message
from email import message_from_bytes
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
import imaplib
import mimetypes
from .tools import Job, job_batch, tdebug \
, patch_import, dev_print, lazy_property \
, table_print, time_diff_str
from .plugin_filesystem import file_name_fix, file_size_str \
, var_get, var_set, file_path_fix
from .plugin_network import html_clean
_CC_LIMIT = 35
_MAX_FILE_LEN = 200
_FILE_EXT = 'eml'
_MAX_ERR_STR_LEN = 200
_LAST_NUM_VAR = 'last_mail_msg_num_in_'

class MailMsg:
	'''
	Represents email message as an object.
	'''

	def __init__(self, login:str, server:str
	, check_only:bool=False, raw_bytes:bytes=b''
	, error:str='', exception:Exception=None
	, sub_rule:Callable=lambda m: ''):
		self.raw_bytes:bytes = raw_bytes
		self.error:str = error
		self.exception:Exception = exception 
		self.login:str = login
		self.server:str = server
		self.dst_dir:str = ''
		self.file_index:int = 0
		if raw_bytes:
			self.size:int = len(raw_bytes)
			self.size_str:str = file_size_str(self.size)
		self.check_only:bool = check_only
		self.sub_rule:Callable = sub_rule
	
	@lazy_property
	def as_str(self)->str:
		'''
		Returns the entire message (including headers)
		as a string.
		'''
		return self._message.as_string()

	@lazy_property
	def _message(self)->Message:
		return message_from_bytes(self.raw_bytes)
	
	@lazy_property
	def _subj_fname(self)->str:
		'''
		Subject as a filesystem safe string (not a full path)
		'''
		return file_name_fix(self.h_subject)

	@lazy_property
	def body(self)->str:
		'''
		Returns message body as text.
		This can be an HTML string (see also **body_text**)
		'''
		body = ''
		charsets = set(('utf-8', 'cp1251'))
		if cs := self._message.get_charset(): charsets.update(cs)
		try:
			if self._message.is_multipart():
				for part in self._message.walk():
					if part.get_content_type() != 'text/plain': continue
					payload = part.get_payload(decode=True)
					for charset in charsets:
						try:
							body += payload.decode(encoding=charset)
						except:
							continue
			else:
				body = self._message.get_payload(decode=True)
				for charset in charsets:
					try:
						body = body.decode(encoding=charset)
					except:
						continue
		except Exception as e:
			dev_print(body := f'body error: {repr(e)}')
		body = body.strip()
		return body

	def _get_header(self, header:str)->str:
		'''
		Returns decoded header as string.
		'''
		hdr_str = ''
		try:
			hdr_str = str(
				make_header(
					decode_header( self._message.get(header) )
				)
			)
		except LookupError:
			dev_print(hdr_str := f'header "{header}" LookupError')
		except TypeError:
			dev_print(hdr_str := f'header "{header}" not found')
		except Exception as e:
			dev_print(hdr_str := f'header "{header}" error: {repr(e)}')
		return hdr_str

	@lazy_property
	def h_date(self)->str:
		'''
		Returns decoded *Date* header.
		'''
		return self._get_header('Date')
	
	@property
	def date_dif(self)->str:
		return time_diff_str(
			parsedate_to_datetime( self.h_date )
			, end=datetime.datetime.now(
				tz=datetime.datetime.now().astimezone().tzinfo
			)
			, no_ms=True
		)

	@lazy_property
	def h_subject(self)->str:
		'''
		Returns decoded *Subject* header.
		'''
		return self._get_header('Subject')

	@lazy_property
	def h_to(self)->str:
		'''
		Returns decoded *To* header.
		'''
		return self._get_header('To')

	@lazy_property
	def h_from(self)->str:
		'''
		Returns decoded *From* header.
		'''
		return self._get_header('From')

	@lazy_property
	def body_text(self)->str:
		'''
		Returns the email body text cleaned of HTML tags
		and empty space, including line breaks.
		'''
		return html_clean(self.body, is_mail=True)
	
	@lazy_property
	def fullpath(self)->str:
		' Full path for the message file '
		return file_path_fix(
			(
				self.dst_dir
				, self.sub_rule(self)
				, f'{self.file_index} - {self._subj_fname}.{_FILE_EXT}'
			)
			, len_limit=_MAX_FILE_LEN
		)
	
	def __getattr__(self, name: str):
		if not name.startswith('h_'):
			raise Exception(f'MailMsg unknown attribute: {name}')
		name = name[2:]
		dev_print(f'get: unknown header: "{name}"')
		hdr_str = self._get_header(name)
		setattr(self, 'h_' + name, hdr_str)
		return hdr_str


	def __str__(self):
		return 'MailMsg: ' + self.h_subject[:20]

class _MailLog:

	def __init__(self, prefix:str, login:str, server:str, silent:bool
	, err_lst:list):
		self.prefix:str = prefix
		self.login:str = login
		self.server:str = server
		self.silent:bool = silent
		self.err_lst:list = err_lst
	
	def log(self, msg:str):
		if isinstance(msg, Exception):
			msg = ( f'exception «{repr(msg)}»'
			+ f' at line {msg.__traceback__.tb_lineno}' )
		else:
			msg = str(msg)
		msg = f'{self.prefix} {self.login}@{self.server}: {msg}'
		if 'error' in msg.lower(): self.err_lst.append(msg)
		if self.silent:
			tdebug(msg)
		else:
			print(msg)

def mail_send(
	recipient:str
	, subject:str
	, message:str
	, server:str
	, port:int
	, login:str
	, password:str
	, from_name:str=''
	, attachment:str=''
	, reply_to:str=''
)->Tuple[bool, str]:
	'''
	Send mail. Returns (True, None) on success or
	(False, 'error text').

	*recipient* - emails separated with commas.

	*attachment* - the full path to a file or
	a list of such paths.

	'''
	
	context = ssl.create_default_context()
	msg = EmailMessage()
	msg['Subject'] = subject
	if from_name:
		msg['From'] = f'{from_name} <{login}>'
	else:
		msg['From'] = login
	msg.set_content(message, cte='base64')
	if reply_to: msg.add_header('Reply-To', reply_to)
	if isinstance(attachment, str): attachment = [attachment]
	for attach in attachment:
		if not attach: continue
		if not os.path.isfile(attach):
			raise Exception('wrong attachment')
		filetype, encoding = mimetypes.guess_type(attach)
		if filetype is None or encoding is not None:
			filetype = 'application/octet-stream'
		maintype, subtype = filetype.split('/', 1)
		with open(attach, 'rb') as fp:
			msg.add_attachment(
				fp.read()
				, maintype=maintype
				, subtype=subtype
				, filename=os.path.basename(attach)
			)
	
	try:
		with smtplib.SMTP_SSL(host=server, port=port
		, context=context) as smtp:
			smtp.login(login, password)
			smtp.send_message(
				msg
				, to_addrs=recipient.split(',')
			)
	except smtplib.SMTPResponseException as e:
		return False, e.smtp_error.decode()
	except Exception as e:
		tdebug(repr(e))
		return False, repr(e)
	return True, ''
	
def mail_send_batch(recipients:str=''
, cc_limit:int=_CC_LIMIT, **mail_send_args)->List[str]:
	'''
	Send email to many recipients.
	Returns list of errors if any.
	
	*recipients* - list of emails or
	a string with comma separated emails.

	*cc_limit* - carbon copy limit of the server.

	'''
	
	errors = []
	if isinstance(recipients, str):
		rec_li = recipients.replace(' ', '').split(',')
	rec_li = list(set(rec_li))
	rec_li = [rec_li[x:x+cc_limit] for x in range(0, len(rec_li), cc_limit)]
	for rec in rec_li:
		errors.extend( mail_send(
			recipient=','.join(rec)
			, **mail_send_args
		)[1] )
	return errors

def mail_check(server:str, login:str, password:str
, folders:list=['inbox'], msg_status:str='UNSEEN'
, headers:tuple=('subject', 'from', 'to', 'date')
, silent:bool=True)->Tuple[ List[MailMsg], List[str] ]:
	'''
	Returns subjects of messages with *msg_status*
	on the server in specified folder(s).
	Returns list of MailMsg and list of errors.

	*headers* - message headers to fetch. You can access them later
	in MailMsg attributes.

	'''
	msgs:list = []
	errors:list = []
	log = _MailLog(prefix='check', login=login, server=server
	, silent=silent, err_lst=errors).log
	try:
		imap = imaplib.IMAP4_SSL(server)
		try:
			imap.login(login, password)
		except Exception as e:
			log(f'login error: {repr(e)}')
			return [], errors
		log('login OK')
		for folder in folders:
			log(f'select folder «{folder}»')
			status, data = imap.select(folder, True)
			if status != 'OK':
				log(f'select error ({status}): {data}')
				continue
			log('select "OK", now search in folder')
			status, msg_ids = imap.search(None, msg_status)
			if status != 'OK':
				log(f'imap search error ({status}): {msg_ids}')
				continue
			msg_ids = msg_ids[0].split()
			msg_cnt = len(msg_ids)
			log(f'{msg_cnt} «{msg_status}» messages in «{folder}»')
			if not msg_cnt: continue
			for msg_id in msg_ids:
				for att in range(3):
					time.sleep(att * 2)
					status, data = imap.fetch(
						msg_id
						, '(BODY.PEEK[HEADER.FIELDS ({})])'.format(
							' '.join(h.upper() for h in headers)
						).encode()
					)
					if status == 'OK': break
					log(f'fetch attempt {att} ({status}): {data}')
				else:
					log(f'fetch error ({status}): {data}')
					continue
				msgs.append( MailMsg(login=login, server=server
				, raw_bytes=data[0][1], check_only=True) )
		log(imap.close())
		log(imap.logout())
	except Exception as e:
		log(e)
	return msgs, errors

def _get_last_index(folder:str)->int:
	''' Get the last used message number '''
	num = var_get(_LAST_NUM_VAR + folder)
	if num: return int(num)
	try:
		fi_list = glob.glob(folder + f'\\*.{_FILE_EXT}')
		if fi_list:
			num = max([
				int(
					os.path.basename(f).split()[0]
				) for f in fi_list
			])
		else:
			num = 0
	except Exception as e:
		dev_print(f'last index error: {repr(e)}')
		num = 0
	return num
	
def mail_download(server:str, login:str, password:str
, dst_dir:str, folders:list=['inbox']
, trash_folder:str='Trash', silent:bool=True
, attempts:int=3
, sub_rule:Callable=lambda m: '')->Tuple[List[MailMsg], List[str] ]:
	'''
	Downloads all messages from the server to the
	specified directory (*dst_dir*).
	Returns tuple with messages (MailMsg) and errors (str).

	*trash_folder* - IMAP folder where deleted messages
	are moved. For GMail use `None`.

	*folders* - list of IMAP folders to check.

	*sub_rule* is a function that accepts *MailMsg* instance
	and which returns the name of the subfolder. Example:

		def _mail_sort(msg: MailMsg)->str:
			if 'amazon.com' in msg.h_from.lower():
				return 'shopping'
			return ''

	'''
	errors = []
	last_index = 0
	msgs = []
	log = _MailLog(prefix='downl', login=login, server=server
	, silent=silent, err_lst=errors).log
	
	try:
		log('connect to server')
		imap = imaplib.IMAP4_SSL(server)
		try:
			imap.login(login, password)
		except Exception as e:
			log(f'login error: {repr(e)}')
			return [], errors
		log('login OK')
		for folder in folders:
			log(f'select folder «{folder}»')
			status, mail_count = imap.select(folder, readonly=False)
			if status != 'OK':
				log(f'select error («{folder}»): {status} {mail_count}')
				continue
			log('select is OK')
			cnt = int(mail_count[0].decode('utf-8'))
			log(f'found {cnt} messages in «{folder}» folder')
			status, search_data = imap.search(None, 'ALL')
			if status != 'OK':
				log(f'search error: {status} {search_data}')
				continue
			for msg_id in search_data[0].split():
				for att in range(attempts):
					time.sleep(att * 2)
					status, fetch_data = imap.fetch(msg_id, '(RFC822)')
					if status == 'OK': break
					log(f'fetch attempt {att} ({status}): {data}')
				else:
					log(f'fetch error ({status}): {fetch_data}')
					continue
				msg = MailMsg(login=login, server=server
				, raw_bytes=fetch_data[0][1], sub_rule=sub_rule)
				log(f'message fetched ({msg_id}): «{msg.h_subject}»')
				if last_index == 0:
					last_index = _get_last_index(dst_dir) + 1
				else:
					last_index += 1
				msg.dst_dir = dst_dir
				msg.file_index = last_index
				try:
					with open(msg.fullpath, 'bw') as f:
						f.write(msg.raw_bytes)
					file_ok = True
				except Exception as e:
					file_ok = False
					log(f'file write error: {repr(e)}')
					try:
						os.remove(msg.fullpath)
					except:
						log(f'file deletion error')
				msgs.append(msg)
				if file_ok:
					var_set(_LAST_NUM_VAR + dst_dir, last_index)
					if trash_folder:
						status, data = imap.copy(msg_id, trash_folder)
						if status == 'OK':
							imap.store(msg_id, '+FLAGS', '\\Deleted')
						else:
							log(f'message move error ({status}): {data}')
					else:
						imap.store(msg_id, '+FLAGS', '\\Deleted')
			log(imap.expunge())
			log(imap.close())
			log(imap.logout())
	except Exception as e:
		log(e)
	return msgs, errors

def mail_download_batch(mailboxes:list, dst_dir:str, timeout:int=60
, log_file:str=r'mail_errors.log', err_thr:int=8
, silent:bool=True)->Tuple[ List[MailMsg], List[str] ]:
	''' Downloads (or checks) all mailboxes in list of dictionaries
		with parameters for mail_download or mail_check.
		In mailboxes 'check_only' - do not download, only count the number
		of unread messages.
		Returns a list with subjects and boolean warning if too many errors
		detected.
	'''
	def write_log()->tuple:
		'''
		Write errors to the log. Returns True and log file name.
		'''
		try:
			if errors:
				with open(log_file, 'at+') as fd:
					for er in errors:
						fd.write('%s\t%s\n' %
							(time.strftime('%Y-%m-%d %H:%M:%S'), er))
			else:
				try:
					open(log_file, 'w').close()
				except FileNotFoundError:
					pass
			return True, log_file
		except Exception as e:
			return False, 'write_log error: ' + repr(e)
		
	def log_warning()->tuple:
		''' Returns True and last line if there is too many errors
			in log file.
		'''
		if not os.path.exists(log_file): return False, None
		if os.path.getsize(log_file) == 0:
			return False, None
		try:
			with open(log_file, 'rt') as f:
				lines = f.readlines()
				if len(lines) > err_thr:
					return True, lines[-1][:-1]
				else:
					return False, None
		except Exception as e:
			return True, 'Failed to open log file: ' + str(e)
	try:
		jobs = []
		for box in mailboxes:
			box['silent'] = silent
			target = mail_download
			if box.get('check_only'):
				target = mail_check
			else:
				box['dst_dir'] = dst_dir
			jobs.append( Job(
				target
				, **{k:box[k] for k in box if k!='check_only'}
			) )
		errors = []
		msgs = []
		table = [('Login', 'Time')]
		job: Job
		for job in job_batch(jobs, timeout=timeout):
			if job.error:
				table.append( ('{}@{}'.format(job.kwargs['login']
				, job.kwargs['server']), 'error') )
				errors.append(
					'{}@{} error: {}'.format(
						job.kwargs['login']
						, job.kwargs['server']
						, job.result
					)
				)
				continue
			msgs.extend(job.result[0])
			errors.extend(job.result[1])
			table.append( ('{}@{}'.format(job.kwargs['login']
			, job.kwargs['server']), job.time) )
		if not silent: table_print(table, use_headers=True)
		status, data = write_log()
		if not status: errors.append(f'logging error: {data}')
		warning, last_error = log_warning()
		if warning:
			if len(last_error)> _MAX_ERR_STR_LEN:
				last_error = last_error[:_MAX_ERR_STR_LEN] + '...'
			errors.append(
				f'Too many errors! The last one: {last_error}'
			)
	except Exception as e:
		dev_print( m := f'mail_download_batch exception: {repr(e)}'
		+ f' at line {e.__traceback__.tb_lineno}')
		errors.append(m)
	return msgs, errors
	
if __name__ != '__main__': patch_import()
