
import subprocess
import smtplib
import ssl
import argparse
import sys
import glob
import os
import time
from email.message import EmailMessage
import imaplib
from email import message_from_bytes
from email.header import Header, decode_header, make_header
import mimetypes
from .tools import Job, job_batch, var_get, var_set, tprint \
, patch_import
from .plugin_filesystem import file_name_fix, file_size_str
_CC_LIMIT = 35
_errors = []
_MAX_FILE_LEN = 200
_MAX_ERR_STR_LEN = 200
_MAX_TITLE_LEN = 80
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
	def __init__(self, subject:str='', content:dict=''
	, fullpath:str='', login:str='', server:str=''
	, size_str:str='', check_only:bool=False):
		self.subject = subject
		self.fullpath = fullpath
		self.login = login
		self.server = server
		self.size_str = size_str
		self.content = content
		self.check_only = check_only

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
	):
	''' Send email.
		recipient - emails separated with commas.
		Returns (True, None) on success or
		(False, 'error text').
	'''
	context = ssl.create_default_context()
	msg = EmailMessage()
	msg['Subject'] = subject
	msg['From'] = f'"{from_name}" <{smtp_user}>'
	msg.set_content(message, cte='base64')
	if reply_to != '': msg.add_header('Reply-To', reply_to)
	if attachment:
		if os.path.isfile(attachment):
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
				, to_addrs = recipient.split(',')
			)
	except smtplib.SMTPResponseException as e:
		_errors.append(f'error smtplib exception: {e.smtp_code}'
		+ f' ({e.smtp_error.decode()[:100]})')
		return False, e.smtp_error.decode()[:100]
	except Exception as e:
		print(repr(e)[:100])
		_errors.append(f'error SMTP: {repr(e)[:100]}')
		return False, repr(e)[:100]
	return True, None
	
def mail_send_batch(recipients:str='', **mail_send_args):
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
, silent:bool=True)->tuple:
	'''
	Counts the number of messages with *msg_status*
	on the server.
	Returns (msg_num:int, errors:list)

		>>>(5, [])
		or
		>>>(0, ['login failed'])
	'''
	msg_num = 0
	errors = []

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
				pr(f'error imap folder: {status} {data}', True)
				continue
			pr('select status "OK", now search in folder')
			status, msg_ids = imap.search(None, msg_status)
			if status == 'OK':
				count = len(msg_ids[0].split())
				pr(f'{count} "{msg_status}" messages in "{folder}"')
				msg_num += count
			else:
				pr(f'error imap search: {status} {msg_ids}', True)
		imap.close()
		imap.logout()
	except Exception as e:
		pr(f'mail_check exception: {repr(e)}', True)
	return msg_num, errors

def _get_last_index(folder:str)->int:
	''' Get the last used message number '''
	num = var_get(_LAST_NUM_VAR + folder)
	if num: return int(num)
	try:
		fi_list = glob.glob(folder + r'\*.eml')
		if fi_list:
			num = max(
				[int(os.path.basename(x).split()[0]) for x in fi_list]
			)
		else:
			num = 0
	except Exception as e:
		print(f'error last index: {repr(e)}')
		num = 0
	return num
	
def mail_download(server:str, login:str, password:str
, output_dir:str, folders:list=['inbox']
, trash_folder:str='Trash', silent:bool=True)->tuple:
	'''
	Downloads all messages from the server to the
	specified directory (*output_dir*).
	*trash_folder* - IMAP folder where deleted messages
	are moved. For GMail use None.
	
	Returns tuple: (messages:list, errors:list).
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
				msg = MailMsg(login=login, server=server)
				status, msg_data = imap.fetch(msg_id, '(RFC822)')
				if status != 'OK':
					pr(f'error imap fetch: {status} {msg_data}', True)
					continue
				msg_raw = msg_data[0][1]
				msg.size_str = file_size_str(len(msg_raw))
				msg.content = message_from_bytes(msg_raw)
				try:
					msg.subject = str(
						make_header(decode_header(msg.content['Subject']))
					)
				except LookupError:
					pr('bad subject', True)
					msg.subject = 'bad_subject'
				except TypeError:
					pr('no subject')
					msg.subject = 'no_subject'
				except Exception as e:
					pr(f'subject error: {repr(e)}', True)
					msg.subject = 'error_subject'
				msg.subject_fix = file_name_fix(msg.subject)
				if last_index == 0:
					last_index = _get_last_index(output_dir) + 1
				else:
					last_index += 1
				msg.fullpath = os.path.join(output_dir
					, f'{last_index} - {msg.subject_fix}.eml')
				if len(msg.fullpath) > _MAX_FILE_LEN:
					pr(f'name too long (len={len(msg.fullpath)}):\n{msg.subject}\n')
					new_len = (
						_MAX_FILE_LEN
						- len(str(last_index))
						- len(output_dir)
						- 11
					)
					msg.subject_fix = msg.subject_fix[:new_len]
					msg.fullpath = os.path.join(output_dir
						, f'{last_index} - {msg.subject_fix}....eml')
				try:
					with open(msg.fullpath, 'bw') as f:
						f.write(msg_raw)
					file_ok = True
				except Exception as e:
					file_ok = False
					pr(f'file write error: {repr(e)}', True)
				msgs.append(msg)
				if file_ok:
					var_set(_LAST_NUM_VAR + output_dir, last_index)
					if trash_folder:
						status, data = imap.copy(msg_id, trash_folder)
						if status == 'OK':
							imap.store(msg_id, '+FLAGS', '\\Deleted')
						else:
							pr(f'message move error: {status} {data}', True)
					else:
						imap.store(msg_id, '+FLAGS', '\\Deleted')
			pr('expunge')
			imap.expunge()
			pr('close')
			imap.close()
			pr('logout')
			imap.logout()
	except Exception as e:
		tprint(f'mail_download {login}@{server} exception: {repr(e)}')
		pr(f'general error: {e}', True)
	return msgs, errors

def mail_download_batch(mailboxes:list, output_dir:str, timeout:int=60
, log_file:str=r'mail_errors.log', err_thr:int=8
, silent:bool=True)->tuple:
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
		for job in job_batch(jobs, timeout=timeout):
			if job.error:
				errors.append(
					'{}@{} error: {}'.format(
						job.kwargs['login']
						, job.kwargs['server']
						, job.result
					)
				)
				continue
			if job.func == mail_check:
				if job.result[0]:
					msgs.append( MailMsg(
						subject=str(job.result[0])
						, login=job.kwargs['login']
						, server=job.kwargs['server']
						, check_only=True
					) )
				errors.extend(job.result[1])
			else:
				msgs.extend(job.result[0])
				errors.extend(job.result[1])
			if not silent:
				print(
					'{}\t\t{}'.format(job.kwargs['login'], job.time)
				)
		status, data = write_log()
		if not status: errors.append(f'Logging error:\r\n{data}')
		warning, last_error = log_warning()
		if warning:
			if len(last_error)> _MAX_ERR_STR_LEN:
				last_error = last_error[:_MAX_ERR_STR_LEN] + '...'
			errors.append(
				f'Too many errors! The last one:\r\n{last_error}'
			)
	except Exception as e:
		errors.append(f'mail_download_batch exception: {repr(e)}')
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
