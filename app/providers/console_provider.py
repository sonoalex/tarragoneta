"""
Console email provider for development/testing
Prints emails to console instead of sending them
"""
from app.providers.base import EmailProvider
from flask import current_app


class ConsoleEmailProvider(EmailProvider):
    """Provider that prints emails to console (for development/testing)"""
    
    def is_available(self, app=None) -> bool:
        """Console provider is always available"""
        return True
    
    def send_email(self, to, subject, html, sender=None, reply_to=None):
        """Print email to console instead of sending"""
        config = current_app.config
        
        # Get sender
        default_sender = sender or config.get('MAIL_DEFAULT_SENDER', 'Tarracograf <hola@tarracograf.cat>')
        
        # Print email details to console
        print("\n" + "=" * 80)
        print("📧 EMAIL (Console Provider - Not Sent)")
        print("=" * 80)
        print(f"From: {default_sender}")
        print(f"To: {to}")
        if reply_to:
            print(f"Reply-To: {reply_to}")
        print(f"Subject: {subject}")
        print("-" * 80)
        print("HTML Content:")
        print(html)
        print("=" * 80 + "\n")
        
        current_app.logger.info(f'[EMAIL CONSOLE] Email printed to console: {to} - {subject}')
        return True

