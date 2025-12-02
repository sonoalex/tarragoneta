"""
Base class for email providers
"""
from abc import ABC, abstractmethod


class EmailProvider(ABC):
    """Abstract base class for email providers"""
    
    @abstractmethod
    def is_available(self, app=None) -> bool:
        """
        Check if this provider is available/configured
        
        Args:
            app: Optional Flask app instance (for use outside request context)
        """
        pass
    
    @abstractmethod
    def send_email(self, to, subject, html, sender=None, reply_to=None) -> bool:
        """
        Send an email
        
        Args:
            to: Email address or list of addresses
            subject: Email subject
            html: HTML content of the email
            sender: Sender email address (optional, uses default if not provided)
            reply_to: Reply-to email address (optional)
        
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        pass

