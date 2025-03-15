
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

def send_email_notification(recipient_email: str, game_name: str, price_info: dict) -> bool:
    """Send email notification about price changes"""
    try:
        sender_email = os.getenv("NOTIFICATION_EMAIL")
        password = os.getenv("EMAIL_PASSWORD")
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Price Drop Alert: {game_name}"
        
        body = f"Price drop for {game_name}!\n\n"
        for store, info in price_info.items():
            body += f"Store: {store}\n"
            body += f"Current Price: {info['current']}\n"
            body += f"Original Price: {info['original']}\n"
            body += f"Discount: {info['discount_percent']}%\n\n"
            
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
            
        return True
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        return False
