import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# from django.core.mail.message import EmailMultiAlternatives
import os
from django.template.loader import render_to_string

def send_password_token(to_email, key, token_activation_code, email_port, sender_email, sender_password):
    title = 'MediConnect Password Reset'
    host = os.getenv('FRONTEND_URL', 'http://localhost:3000')  # Default fallback
    token_page = f'{host}/reset-password/{token_activation_code}/confirm-token'
    
    if not all([to_email, sender_email, sender_password]):
        print("Error: Missing required email parameters")
        return False
    
    try:
        # Render HTML template - make sure this path matches your actual template
        mail_body = render_to_string('emails/password/password_token.html',
                                   {'email': to_email, 'key': key, 'token_page': token_page})
        
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = title
        
        part2 = MIMEText(mail_body, 'html')
        # msg.attach(part1)
        msg.attach(part2)
        
        # Send the email
        with smtplib.SMTP('smtp.gmail.com', email_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        
        print(f"Password reset email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f'Failed to send email to {to_email}')
        print(f'Error details: {str(e)}')
        return False
    

def send_password_was_reset_email(to_email, email_port, sender_email, sender_password):
    title = 'MediConnect Password Reset Successful'
    body = 'Your password has been successfully reset. If you did not initiate this change, please contact support immediately.'
    
    if not all([to_email, sender_email, body, title, sender_password]):
        print("Error: Missing required email parameters")
        return False
    
    mail_body = render_to_string('emails/anymail.html', {'email': to_email, 'title': title, 'content': body})
    
    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = title

    msg.attach(MIMEText(mail_body, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', email_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False



def password_url_email(to_email, email_port, sender_email, body, subject, sender_password):
    if not all([to_email, sender_email, body, subject, sender_password]):
        print("Error: Missing required email parameters")
        return False
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', email_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    

    

