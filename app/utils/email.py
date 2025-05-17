import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import traceback
import ssl
from config import (
    EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, 
    EMAIL_PASSWORD, EMAIL_FROM, FRONTEND_URL
)

def send_email(to_email, subject, html_content):
    """Send an email with the given parameters."""
    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = EMAIL_FROM
    message["To"] = to_email
    
    # Add HTML content
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    try:
        # Print debug info
        print(f"Attempting to send email to {to_email}")
        print(f"Using SMTP server: {EMAIL_HOST}:{EMAIL_PORT}")
        print(f"Using username: {EMAIL_USERNAME}")
        
        # Create a secure SSL context
        context = ssl.create_default_context()
        
        # Connect to SMTP server
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.set_debuglevel(1)  # Enable verbose debug output
            server.ehlo()  # Can be omitted
            server.starttls(context=context)  # Secure the connection
            server.ehlo()  # Can be omitted
            
            # Login
            print("Attempting to login...")
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            print("Login successful")
            
            # Send email
            print("Sending email...")
            server.sendmail(EMAIL_FROM, to_email, message.as_string())
            print("Email sent successfully")
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        print(traceback.format_exc())  # Print full traceback
        return False

def send_password_reset_email(email, token, username):
    """Send a password reset email with a reset link."""
    subject = "Password Reset Request"
    
    # Create HTML content
    html_content = f"""
    <h1>Password Reset Request</h1>
    <p>Hello {username},</p>
    <p>We received a request to reset your password. If you didn't make this request, you can ignore this email.</p>
    <p>To reset your password, please use the token below with the reset-password API endpoint:</p>
    <p><strong>Your reset token:</strong> {token}</p>
    <p>This token will expire in 24 hours.</p>
    <p>Thank you,</p>
    <p>The File Encryption API Team</p>
    """
    
    # Send email and return result
    result = send_email(email, subject, html_content)
    print(f"Email sending result: {result}")
    return result