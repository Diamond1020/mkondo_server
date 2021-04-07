import sendgrid
import os
from sendgrid.helpers.mail import *

def send_mail(to, subject, html_content):
    """
    Send an email
    """
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    from_email = Email(os.environ.get('SENDGRID_DEFAULT_FROM'))
    to_email = To(to)
    subject = subject
    content = Content('text/html', html_content)
    mail = Mail(from_email, to_email, subject, html_content=content)
    response = sg.client.mail.send.post(request_body=mail.get())
