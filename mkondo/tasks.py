import os

import sendgrid
from sendgrid.helpers.mail import *

from mkondo import celery

@celery.task
def send_mail(to, subject, html_content):
    """
    Send an email
    """
    api_key = os.environ.get('SENDGRID_API_KEY')
    sg = sendgrid.SendGridAPIClient('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')
    from_email = Email('mkondoapp@gmail.com')
    to_email = To(to)
    subject = subject
    content = Content('text/html', html_content)
    mail = Mail(from_email, to_email, subject, html_content=content)
    response = sg.client.mail.send.post(request_body=mail.get())
