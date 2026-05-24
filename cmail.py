import smtplib
from email.message import EmailMessage
def send_mail(to,subject,body):
    server = smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('saisrikanth.s1105@gmail.com','zmlp fvxc bxuh ytqg')
    msg = EmailMessage()
    msg['FROM'] = 'saisrikanth.s1105@gmail.com'
    msg['SUBJECT'] = subject
    msg['TO'] = to
    msg.set_content(body)
    server.send_message(msg)
    server.close()