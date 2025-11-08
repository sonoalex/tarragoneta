"""
WSGI entry point for production deployment
This file is used by Gunicorn and other WSGI servers
"""
from app import create_app
import os

# Create app instance for production
app = create_app('production')

if __name__ == '__main__':
    # This allows running directly: python wsgi.py
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

