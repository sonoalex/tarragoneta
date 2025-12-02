"""
Email providers for Tarracograf
Supports multiple email providers (SMTP, Console)
"""
from app.providers.base import EmailProvider
from app.providers.smtp_provider import SMTPEmailProvider
from app.providers.console_provider import ConsoleEmailProvider

__all__ = ['EmailProvider', 'SMTPEmailProvider', 'ConsoleEmailProvider']

