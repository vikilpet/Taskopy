
import subprocess
import smtplib
import ssl
import argparse
import sys
import os
import time
from email.message import EmailMessage
import mimetypes

CC_LIMIT = 35
_errors = []

def _parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('--receiver_email', '-r', help='Email(s) of receiver(s)'
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

def send_email(
		receiver_email:str
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
		receiver_email - emails separated with commas.
		Return True on success or False and error
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
	
	'''
	with open('outgoing.msg', 'wb') as f:
		f.write(bytes(msg))
	'''
	try:
		with smtplib.SMTP_SSL(smtp_server, smtp_port
								, context=context) as server:
			server.login(smtp_user, smtp_password)
			server.send_message(
				msg
				, to_addrs = receiver_email.split(',')
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
	
def send_email_bulk(receiver_email:str='', subject:str='Test subject'
	, from_name:str='Script', reply_to:str=''
	, message:str='Test message', attachment:str='', cc_limit:int=-1):
	''' Send email to many recipients
		receiver_email - emails separated with commas
	'''
	rec_li = receiver_email.replace(' ', '').split(',')
	rec_li = list(set(rec_li))
	if cc_limit == -1: cc_limit = CC_LIMIT
	recipients = [rec_li[x:x+cc_limit] for x in range(0, len(rec_li), cc_limit)]
	for r in recipients:
		send_email(
			receiver_email = ','.join(r)
			, subject = subject
			, from_name = from_name
			, reply_to = reply_to
			, message = message
			, attachment = attachment
		)

def main():
	if len(sys.argv) > 3:
		args = _parse_args()
		try:
			send_email_bulk(**vars(args))
			if len(_errors): sys.exit(3)
		except Exception as e:
			sys.exit(2)
		sys.exit(0)
	else:
		print(f'Not enough arguments!')
		sys.exit(1)
	
if __name__ == '__main__': main()
	