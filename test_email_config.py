#!/usr/bin/env python
"""Test script to verify email configuration"""
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

print("=" * 60)
print("Email Configuration Test")
print("=" * 60)
print()

# Check mail configuration
mail_username = os.environ.get('MAIL_USERNAME', '')
mail_password = os.environ.get('MAIL_PASSWORD', '')
mail_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
mail_port = os.environ.get('MAIL_PORT', '587')

print(f"MAIL_SERVER: {mail_server}")
print(f"MAIL_PORT: {mail_port}")
print(f"MAIL_USERNAME: {mail_username}")
print(f"MAIL_PASSWORD: {'*' * len(mail_password) if mail_password else 'NOT SET'} ({len(mail_password)} chars)")
print()

# Check if password looks like App Password (16 chars, no spaces)
if mail_password:
    if len(mail_password) == 16 and ' ' not in mail_password:
        print("✅ Password format looks correct (16 chars, no spaces)")
    elif ' ' in mail_password:
        print("⚠️  WARNING: Password contains spaces! Remove them.")
    elif len(mail_password) != 16:
        print(f"⚠️  WARNING: Password length is {len(mail_password)}, should be 16")
    else:
        print("⚠️  Password format may be incorrect")
else:
    print("❌ MAIL_PASSWORD is not set!")

print()
print("=" * 60)
print("Testing SMTP connection...")
print("=" * 60)

try:
    import smtplib
    from email.mime.text import MIMEText
    
    if not mail_username or not mail_password:
        print("❌ Cannot test: MAIL_USERNAME or MAIL_PASSWORD not set")
    else:
        # Test connection
        server = smtplib.SMTP(mail_server, int(mail_port))
        server.starttls()
        print("✅ TLS connection established")
        
        try:
            server.login(mail_username, mail_password)
            print("✅ Authentication successful!")
            server.quit()
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ Authentication failed: {e}")
            print()
            print("Possible issues:")
            print("1. App Password is incorrect")
            print("2. App Password has spaces (remove them)")
            print("3. 2-Step Verification is not enabled")
            print("4. Wrong email address")
            server.quit()
        except Exception as e:
            print(f"❌ Error: {e}")
            server.quit()
            
except ImportError:
    print("⚠️  smtplib not available")
except Exception as e:
    print(f"❌ Connection error: {e}")

