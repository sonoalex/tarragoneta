"""
Logging configuration for the application
"""
import os
import logging
from logging.handlers import RotatingFileHandler
import re


def setup_logging(app):
    """Configure logging for the application"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # File handler (both development and production)
    file_handler = RotatingFileHandler(
        'logs/tarracograf.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    if not app.debug:
        # Production logging - only file
        app.logger.setLevel(logging.INFO)
        # Only log startup message if not silenced
        if not os.environ.get('FLASK_SILENT_STARTUP'):
            app.logger.info('Tarracograf startup')
    else:
        # Development logging - console + file
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)
        # Only log startup message if not silenced
        if not os.environ.get('FLASK_SILENT_STARTUP'):
            app.logger.info('Tarracograf startup (DEBUG mode)')
    
    # Log configuration on startup (only if not silenced)
    if not os.environ.get('FLASK_SILENT_STARTUP'):
        _log_startup_configuration(app)


def _log_startup_configuration(app):
    """Log application configuration on startup"""
    app.logger.info(f"Environment: {app.config['ENV']}")
    app.logger.info(f"Debug mode: {app.config['DEBUG']}")
    
    # Mask password in logs
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if '@' in db_uri:
        db_uri_display = re.sub(r':([^:@]+)@', r':****@', db_uri)
    else:
        db_uri_display = db_uri
    app.logger.info(f"Database: {db_uri_display}")
    
    # Log environment variables status (for debugging)
    env_vars_to_check = ['SECRET_KEY', 'SECURITY_PASSWORD_SALT', 'STRIPE_PUBLISHABLE_KEY', 'STRIPE_SECRET_KEY']
    app.logger.info("Environment variables status:")
    for var in env_vars_to_check:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if 'SECRET' in var or 'KEY' in var or 'SALT' in var:
                masked = value[:4] + '****' + value[-4:] if len(value) > 8 else '****'
                app.logger.info(f"  ✓ {var}: {masked} (set)")
            else:
                app.logger.info(f"  ✓ {var}: {value[:20]}... (set)")
        else:
            app.logger.warning(f"  ✗ {var}: not set (using default)")

