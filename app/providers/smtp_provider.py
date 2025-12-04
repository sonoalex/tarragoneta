"""
SMTP email provider using Flask-Mail
Used for local development with Gmail SMTP
"""
from app.providers.base import EmailProvider
from flask import current_app
from flask_mail import Message
import threading
import queue as queue_module


class SMTPEmailProvider(EmailProvider):
    """Provider using SMTP (Flask-Mail) - for local development"""
    
    def is_available(self, app=None) -> bool:
        """Check if SMTP is configured"""
        # Use provided app or current_app
        if app:
            config = app.config
        else:
            from flask import current_app
            config = current_app.config
        
        # Check if SMTP is suppressed (development mode)
        if config.get('MAIL_SUPPRESS_SEND', False):
            return False
        
        # Check if SMTP server and credentials are configured
        mail_server = config.get('MAIL_SERVER')
        mail_username = config.get('MAIL_USERNAME')
        mail_password = config.get('MAIL_PASSWORD')
        
        return bool(mail_server and mail_username and mail_password)
    
    def send_email(self, to, subject, html, sender=None, reply_to=None):
        """Send email via SMTP using Flask-Mail"""
        if current_app.config.get('MAIL_SUPPRESS_SEND', False):
            current_app.logger.info(f'[EMAIL SUPPRESSED] To: {to}, Subject: {subject}')
            return True
        
        try:
            from app.extensions import mail
            import os
            
            # Get sender from config or parameter
            default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'Tarracograf <hola@tarracograf.cat>')
            email_sender = sender or default_sender
            
            current_app.logger.info(f'[EMAIL DEBUG] Creating SMTP message for {to}...')
            msg = Message(
                subject=subject,
                recipients=[to] if isinstance(to, str) else to,
                html=html,
                sender=email_sender,
                reply_to=reply_to
            )
            
            # Attach logo as inline image with Content-ID
            try:
                logo_path = os.path.join(current_app.static_folder or 'static', 'images', 'tarracograf_blanc1.png')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        logo_data = f.read()
                    msg.attach(
                        'tarracograf_logo.png',
                        'image/png',
                        logo_data,
                        'inline',
                        headers=[['Content-ID', '<logo>']]
                    )
                    current_app.logger.debug('Logo attached to email with Content-ID: logo')
            except Exception as e:
                current_app.logger.warning(f'Could not attach logo to email: {e}')
            
            current_app.logger.info(f'[EMAIL DEBUG] Sending email via SMTP to {to}...')
            
            # Get app instance for thread context
            app_instance = current_app._get_current_object()
            
            # Send email with timeout using threading
            result_queue = queue_module.Queue()
            error_queue = queue_module.Queue()
            
            def send_email_thread():
                # Push application context for the thread
                with app_instance.app_context():
                    try:
                        mail.send(msg)
                        result_queue.put(True)
                    except Exception as e:
                        error_queue.put(e)
            
            # Start thread
            thread = threading.Thread(target=send_email_thread, daemon=True)
            thread.start()
            
            # Wait for result with timeout
            timeout = current_app.config.get('MAIL_TIMEOUT', 10)
            thread.join(timeout=timeout)
            
            if thread.is_alive():
                # Thread is still running - timeout occurred
                current_app.logger.error(f'SMTP email send timeout for {to} after {timeout} seconds')
                return False
            
            # Check for errors
            if not error_queue.empty():
                error = error_queue.get()
                raise error
            
            # Check for success
            if not result_queue.empty():
                return True
            else:
                current_app.logger.error(f'SMTP email send failed for {to}: unknown error')
                return False
                
        except Exception as e:
            current_app.logger.error(f'Error sending email via SMTP to {to}: {str(e)}', exc_info=True)
            return False

