#!/usr/bin/env python
"""Test script to verify email configuration"""
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

print("=" * 60)
print("Email Configuration Test - Hostinger SMTP")
print("=" * 60)
print()

# Check mail configuration
mail_username = os.environ.get('MAIL_USERNAME', '')
mail_password = os.environ.get('MAIL_PASSWORD', '')
mail_server = os.environ.get('MAIL_SERVER', 'smtp.hostinger.com')
mail_port = int(os.environ.get('MAIL_PORT', '465'))
mail_use_ssl = os.environ.get('MAIL_USE_SSL', 'True').lower() in ('true', '1', 'yes')
mail_use_tls = os.environ.get('MAIL_USE_TLS', 'False').lower() in ('true', '1', 'yes')

print(f"MAIL_SERVER: {mail_server}")
print(f"MAIL_PORT: {mail_port}")
print(f"MAIL_USE_SSL: {mail_use_ssl}")
print(f"MAIL_USE_TLS: {mail_use_tls}")
print(f"MAIL_USERNAME: {mail_username}")
print(f"MAIL_PASSWORD: {'*' * len(mail_password) if mail_password else 'NOT SET'} ({len(mail_password)} chars)")
print()

if not mail_username:
    print("❌ MAIL_USERNAME is not set!")
if not mail_password:
    print("❌ MAIL_PASSWORD is not set!")

if mail_username and mail_password:
    print("✅ Credentials are set")
else:
    print("⚠️  Missing credentials - cannot test connection")
    exit(1)

print()
print("=" * 60)
print("Testing SMTP connection...")
print("=" * 60)

try:
    import smtplib
    from email.mime.text import MIMEText
    
    if mail_use_ssl:
        # SSL connection (port 465)
        print(f"Attempting SSL connection to {mail_server}:{mail_port}...")
        try:
            server = smtplib.SMTP_SSL(mail_server, mail_port, timeout=10)
            print("✅ SSL connection established")
            
            try:
                server.login(mail_username, mail_password)
                print("✅ Authentication successful!")
                
                # Try to send a test email
                print()
                print("=" * 60)
                print("Sending test email...")
                print("=" * 60)
                
                test_email = mail_username  # Send to self
                msg = MIMEText("This is a test email from Tarracograf email configuration test.")
                msg['Subject'] = 'Test Email - Tarracograf Configuration'
                msg['From'] = mail_username
                msg['To'] = test_email
                
                server.sendmail(mail_username, [test_email], msg.as_string())
                print(f"✅ Test email sent successfully to {test_email}!")
                print("   Check your inbox to confirm delivery.")
                
                server.quit()
            except smtplib.SMTPAuthenticationError as e:
                print(f"❌ Authentication failed: {e}")
                print()
                print("Possible issues:")
                print("1. Email password is incorrect")
                print("2. Email account doesn't exist in Hostinger")
                print("3. Wrong email address")
                server.quit()
            except Exception as e:
                print(f"❌ Error sending email: {e}")
                server.quit()
                
        except smtplib.SMTPConnectError as e:
            print(f"❌ Connection failed: {e}")
            print()
            print("Trying TLS instead (port 587)...")
            print()
            # Fallback to TLS
            try:
                server = smtplib.SMTP(mail_server, 587, timeout=10)
                server.starttls()
                print("✅ TLS connection established")
                
                try:
                    server.login(mail_username, mail_password)
                    print("✅ Authentication successful with TLS!")
                    server.quit()
                    print()
                    print("💡 Tip: Update your .env to use TLS:")
                    print("   MAIL_PORT=587")
                    print("   MAIL_USE_TLS=True")
                    print("   MAIL_USE_SSL=False")
                except smtplib.SMTPAuthenticationError as e:
                    print(f"❌ Authentication failed: {e}")
                    server.quit()
            except Exception as e:
                print(f"❌ TLS connection also failed: {e}")
                
    elif mail_use_tls:
        # TLS connection (port 587)
        print(f"Attempting TLS connection to {mail_server}:{mail_port}...")
        try:
            server = smtplib.SMTP(mail_server, mail_port, timeout=10)
            server.starttls()
            print("✅ TLS connection established")
            
            try:
                server.login(mail_username, mail_password)
                print("✅ Authentication successful!")
                
                # Try to send a test email
                print()
                print("=" * 60)
                print("Sending test email...")
                print("=" * 60)
                
                test_email = mail_username  # Send to self
                msg = MIMEText("This is a test email from Tarracograf email configuration test.")
                msg['Subject'] = 'Test Email - Tarracograf Configuration'
                msg['From'] = mail_username
                msg['To'] = test_email
                
                server.sendmail(mail_username, [test_email], msg.as_string())
                print(f"✅ Test email sent successfully to {test_email}!")
                print("   Check your inbox to confirm delivery.")
                
                server.quit()
            except smtplib.SMTPAuthenticationError as e:
                print(f"❌ Authentication failed: {e}")
                print()
                print("Possible issues:")
                print("1. Email password is incorrect")
                print("2. Email account doesn't exist in Hostinger")
                print("3. Wrong email address")
                server.quit()
            except Exception as e:
                print(f"❌ Error sending email: {e}")
                server.quit()
        except Exception as e:
            print(f"❌ Connection error: {e}")
    else:
        print("⚠️  Neither SSL nor TLS is enabled. Please set MAIL_USE_SSL=True or MAIL_USE_TLS=True")
            
except ImportError:
    print("⚠️  smtplib not available")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()

