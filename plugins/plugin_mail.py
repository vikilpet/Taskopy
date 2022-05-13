
import smtplib
import ssl
import argparse
import sys
import glob
import os
import time
from typing import Tuple, List
from email.message import EmailMessage, Message
from email import message_from_bytes
from email.header import decode_header, make_header
import imaplib
import mimetypes
from .tools import Job, job_batch, tprint \
, patch_import, dev_print, lazy_property, safe \
, table_print
from .plugin_filesystem import file_name_fix, file_size_str \
, var_get, var_set, file_path_fix
from .plugin_network import html_clean
_CC_LIMIT = 35
_errors = []
_MAX_FILE_LEN = 200
_FILE_EXT = 'eml'
_MAX_ERR_STR_LEN = 200
_LAST_NUM_VAR = 'last_mail_msg_num_in_'

def _parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('--recipient', '-r', help='Email(s) of receiver(s)'
		, type=str, default='')
	parser.add_argument('--subject', '-s', help='Subject', type=str
		, default='Test subject')
	parser.add_argument('--from_name', '-f', help='Sender name', type=str
		, default='Script')
	parser.add_argument('--reply_to', '-rt', help='Reply-to', type=str
		, default='')
	parser.add_argument('--message', '-m', help='Message body', type=str
		, default='Test message')
	parser.add_argument('--attachment', '-a', help='Fullpath to file', type=str
		, default='')
	return parser.parse_args()

class MailMsg:
	'''
	Represents email message as an object.
	'''

	def __init__(self, login:str, server:str
	, check_only:bool=False, raw_bytes:bytes=None
	, error:str=None, exception:Exception=None):
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
		return file_name_fix(self.subject)

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

	@lazy_property
	def subject(self)->str:
		'''
		Returns decoded Subject header.
		'''
		subj = 'no-subject'
		try:
			subj = str(
				make_header(
					decode_header( self._message.get('Subject') )
				)
			)
		except LookupError:
			dev_print(subj := 'subject LookupError')
		except TypeError:
			dev_print(subj := 'no-subject')
		except Exception as e:
			dev_print(subj := f'subject error: {repr(e)}')
		return subj

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
				, f'{self.file_index} - {self._subj_fname}.{_FILE_EXT}'
			)
			, len_limit=_MAX_FILE_LEN
		)

	def __str__(self):
		return 'MailMsg: ' + self.subject[:20]

def mail_send(
		recipient:str
		, subject:str
		, message:str
		, smtp_server:str
		, smtp_port:int
		, smtp_user:str
		, smtp_password:str
		, from_name:str=''
		, attachment:str=''
		, reply_to:str=''
	)->tuple:
	'''
	Send email.
	recipient - emails separated with commas.
	Returns (True, None) on success or
	(False, 'error text').
	'''
	context = ssl.create_default_context()
	msg = EmailMessage()
	msg['Subject'] = subject
	msg['From'] = f'"{from_name}" <{smtp_user}>'
	msg.set_content(message, cte='base64')
	if reply_to: msg.add_header('Reply-To', reply_to)
	if attachment:
		if not os.path.isfile(attachment):
			raise Exception('wrong attachment')
		ctype, encoding = mimetypes.guess_type(attachment)
		if ctype is None or encoding is not None:
			ctype = 'application/octet-stream'
		maintype, subtype = ctype.split('/', 1)
		with open(attachment, 'rb') as fp:
			msg.add_attachment(
				fp.read()
				, maintype=maintype
				, subtype=subtype
				, filename=attachment[attachment.rfind('\\') + 1:]
			)
	try:
		with smtplib.SMTP_SSL(smtp_server, smtp_port
		, context=context) as server:
			server.login(smtp_user, smtp_password)
			server.send_message(
				msg
				, to_addrs=recipient.split(',')
			)
	except smtplib.SMTPResponseException as e:
		_errors.append(f'smtplib error: {e.smtp_code}'
		+ f' ({e.smtp_error.decode()[:100]})')
		return False, e.smtp_error.decode()[:100]
	except Exception as e:
		dev_print(repr(e)[:100])
		_errors.append(f'mail_send error: {repr(e)[:100]}')
		return False, repr(e)[:100]
	return True, None
	
def mail_send_batch(recipients:str=''
, cc_limit:int=-1, **mail_send_args):
	''' Send email to many recipients
		recipient - emails separated with commas
	'''
	rec_li = recipients.replace(' ', '').split(',')
	rec_li = list(set(rec_li))
	if cc_limit == -1: cc_limit = _CC_LIMIT
	recipients = [rec_li[x:x+cc_limit] for x in range(0, len(rec_li), cc_limit)]
	for r in recipients:
		mail_send(
			recipient = ','.join(r)
			, **mail_send_args
		)

def mail_check(server:str, login:str, password:str
, folders:list=['inbox'], msg_status:str='UNSEEN'
, silent:bool=True)->Tuple[ List[MailMsg], List[str] ]:
	'''
	Counts the number of messages with *msg_status*
	on the server.
	Returns (msg_num:int, errors:list)

		>(5, [])
		>(0, ['login failed'])

	'''
	msgs:list = []
	errors:list = []

	def pr(add_text, is_error:bool=False):
		nonlocal errors
		if not silent:
			print (f'mail_check (serv={server}, login={login}): {add_text}')
		if is_error:
			errors.append ( (f'{login}@{server}: {add_text}') )

	try:
		imap = imaplib.IMAP4_SSL(server)
		imap.login(login, password)
		for folder in folders:
			pr(f'select folder "{folder}"')
			status, data = imap.select(folder, True)
			if status != 'OK':
				pr(f'imap select error ({status}): {data}', True)
				continue
			pr('select "OK", now search in folder')
			status, msg_ids = imap.search(None, msg_status)
			if status != 'OK':
				pr(f'imap search error ({status}): {msg_ids}', True)
				continue
			msg_ids = msg_ids[0].split()
			msg_cnt = len(msg_ids)
			pr(f'{msg_cnt} "{msg_status}" messages in "{folder}"')
			if not msg_cnt: continue
			for msg_id in msg_ids:
				for att in range(3):
					time.sleep(att * 2)
					status, data = imap.fetch(
						msg_id
						, '(BODY.PEEK[HEADER.FIELDS (SUBJECT)])'.encode()
					)
					if status == 'OK': break
					pr(f'fetch attempt {att} ({status}): {data}')
				else:
					pr(f'fetch error ({status}): {data}')
					continue
				msgs.append( MailMsg(login=login, server=server
				, raw_bytes=data[0][1], check_only=True) )
		imap.close()
		imap.logout()
	except Exception as e:
		pr(f'mail_check exception: {repr(e)}'
		+ f' at line {e.__traceback__.tb_lineno}', True)
	return msgs, errors

def _get_last_index(folder:str)->int:
	''' Get the last used message number '''
	num = var_get(_LAST_NUM_VAR + folder)
	if num: return int(num)
	try:
		fi_list = glob.glob(folder + f'\\*.{_FILE_EXT}')
		if fi_list:
			num = max(
				[int(os.path.basename(x).split()[0]) for x in fi_list]
			)
		else:
			num = 0
	except Exception as e:
		dev_print(f'last index error: {repr(e)}')
		num = 0
	return num
	
def mail_download(server:str, login:str, password:str
, output_dir:str, folders:list=['inbox']
, trash_folder:str='Trash', silent:bool=True
, attempts:int=3)->Tuple[List[MailMsg], List[str] ]:
	'''
	Downloads all messages from the server to the
	specified directory (*output_dir*).
	
	*trash_folder* - IMAP folder where deleted messages
	are moved. For GMail use None.
	
	Returns tuple with messages (MailMsg) and errors (str).
	'''
	msg_number = 0
	errors = []
	last_index = 0
	msgs = []
	
	def pr(add_text:str, is_error:bool=False):
		nonlocal errors
		if not silent:
			print (f'mail_dl ({login}@{server}): {add_text}')
		if is_error:
			errors.append(f'{login}@{server}: {add_text}')
	try:
		pr('connect to server')
		imap = imaplib.IMAP4_SSL(server)
		pr('login')
		status, data = imap.login(login, password)
		if status != 'OK':
			pr(f'login failed: {status} {data}', True)
			return False, [], errors
		pr('login successful')
		for folder in folders:
			pr(f'select folder {folder}')
			status, mail_count = imap.select(folder, readonly=False)
			if status != 'OK':
				pr(f'select folder error ({folder}): {status} {mail_count}', True)
				continue
			pr('select is "OK"')
			number = int(mail_count[0].decode('utf-8'))
			pr(f'found {number} messages in "{folder}" folder')
			msg_number += number
			status, search_data = imap.search(None, 'ALL')
			if status != 'OK':
				pr(f'error imap search: {status} {search_data}', True)
				continue
			for msg_id in search_data[0].split():
				for att in range(attempts):
					time.sleep(att * 2)
					status, fetch_data = imap.fetch(msg_id, '(RFC822)')
					if status == 'OK': break
				else:
					pr(f'fetch error ({status}): {fetch_data}', True)
					continue
				msg = MailMsg(login=login, server=server
				, raw_bytes=fetch_data[0][1])
				if last_index == 0:
					last_index = _get_last_index(output_dir) + 1
				else:
					last_index += 1
				msg.dst_dir = output_dir
				msg.file_index = last_index
				try:
					with open(msg.fullpath, 'bw') as f:
						f.write(msg.raw_bytes)
					file_ok = True
				except Exception as e:
					file_ok = False
					pr(f'file write error: {repr(e)}', True)
					safe(os.remove)(msg.fullpath)
					continue
				msgs.append(msg)
				if file_ok:
					var_set(_LAST_NUM_VAR + output_dir, last_index)
					if trash_folder:
						status, data = imap.copy(msg_id, trash_folder)
						if status == 'OK':
							imap.store(msg_id, '+FLAGS', '\\Deleted')
						else:
							pr(f'message move error ({status}): {data}', True)
					else:
						imap.store(msg_id, '+FLAGS', '\\Deleted')
			pr('expunge')
			imap.expunge()
			pr('close')
			imap.close()
			pr('logout')
			imap.logout()
	except Exception as e:
		tprint(f'mail_download {login}@{server} exception: {repr(e)}'
		+ f' at line {e.__traceback__.tb_lineno}')
		pr(f'general error: {e}', True)
	return msgs, errors

def mail_download_batch(mailboxes:list, output_dir:str, timeout:int=60
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
		''' Write errors to log. Returns True and log file name.
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
			return False, 'error write_log ' + repr(e)
		
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
			if box.get('check_only', False):
				jobs.append(
					Job(
						mail_check
						, **{k:box[k] for k in box if k!='check_only'}
					)
				)
				continue
			box['output_dir'] = output_dir
			jobs.append(
				Job(
					mail_download
					, **{k:box[k] for k in box if k!='check_only'}
				)
			)
		errors = []
		msgs = []
		table = [('User', 'Time')]
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
	
if __name__ == '__main__':
	if len(sys.argv) > 3:
		args = _parse_args()
		try:
			mail_send_batch(**vars(args))
			if len(_errors): sys.exit(3)
		except:
			sys.exit(2)
		sys.exit(0)
	else:
		print(f'Not enough arguments!')
		sys.exit(1)
else:		
	patch_import()
