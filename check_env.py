#!/usr/bin/env python
"""
Script to check environment variables in Railway
Run this to verify that your environment variables are being loaded correctly
"""
import os

# Try to load dotenv if available (for local testing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

print("=" * 60)
print("Environment Variables Check")
print("=" * 60)
print()

# Required variables
required_vars = {
    'SECRET_KEY': 'Secret key for Flask sessions',
    'SECURITY_PASSWORD_SALT': 'Salt for password hashing',
}

# Optional variables
optional_vars = {
    'DATABASE_URL': 'Database connection string',
    'STRIPE_PUBLISHABLE_KEY': 'Stripe publishable key',
    'STRIPE_SECRET_KEY': 'Stripe secret key',
    'STRIPE_WEBHOOK_SECRET': 'Stripe webhook secret',
    'FLASK_ENV': 'Flask environment (development/production)',
    'PORT': 'Port to listen on (Railway sets this)',
    'RAILWAY_ENVIRONMENT': 'Railway environment indicator',
}

print("Required Variables:")
print("-" * 60)
all_ok = True
for var, description in required_vars.items():
    value = os.environ.get(var)
    if value:
        # Mask sensitive values
        if len(value) > 8:
            masked = value[:4] + '****' + value[-4:]
        else:
            masked = '****'
        print(f"  ✓ {var:25} {masked:20} ({description})")
    else:
        print(f"  ✗ {var:25} NOT SET          ({description})")
        all_ok = False

print()
print("Optional Variables:")
print("-" * 60)
for var, description in optional_vars.items():
    value = os.environ.get(var)
    if value:
        # Mask sensitive values
        if 'SECRET' in var or 'KEY' in var or 'PASSWORD' in var:
            if len(value) > 8:
                masked = value[:4] + '****' + value[-4:]
            else:
                masked = '****'
        else:
            masked = value[:40] + '...' if len(value) > 40 else value
        print(f"  ✓ {var:25} {masked:40} ({description})")
    else:
        print(f"  - {var:25} not set          ({description})")

print()
print("=" * 60)
if all_ok:
    print("✓ All required variables are set!")
else:
    print("✗ Some required variables are missing!")
print("=" * 60)

