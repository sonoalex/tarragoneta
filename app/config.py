import os
import secrets

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    # Database configuration
    # Railway provides DATABASE_URL, but we need to handle PostgreSQL vs SQLite
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///tarragoneta.db')
    # Railway uses postgres:// but SQLAlchemy needs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before using
        'pool_recycle': 300,    # Recycle connections after 5 minutes
    }
    
    # Security
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT', 'tarragoneta-salt-2024')
    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_REGISTERABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_POST_LOGIN_VIEW = 'admin.admin_dashboard'
    SECURITY_POST_LOGOUT_VIEW = 'main.index'
    SECURITY_POST_REGISTER_VIEW = 'main.index'
    SECURITY_UNAUTHORIZED_VIEW = 'main.index'
    SECURITY_LOGIN_USER_TEMPLATE = 'security/login.html'
    SECURITY_REGISTER_USER_TEMPLATE = 'security/register.html'
    
    # Session configuration
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds
    
    # WTF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Babel
    BABEL_DEFAULT_LOCALE = 'ca'
    BABEL_SUPPORTED_LOCALES = ['ca', 'es']
    BABEL_DEFAULT_TIMEZONE = 'Europe/Madrid'
    BABEL_TRANSLATION_DIRECTORIES = 'babel/translations'
    
    # File uploads
    # Use static/uploads in both local and production
    # In Railway, mount the volume at static/uploads
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Stripe
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    
    # Mail configuration (Gmail)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'hola@latarragoneta.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')  # App password from Google
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'Tarragoneta <hola@latarragoneta.com>')
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'False').lower() in ('true', '1', 'yes')
    
    # Admin email for notifications
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'hola@latarragoneta.com')
    
    # Inventory auto-resolve settings
    INVENTORY_AUTO_RESOLVE_THRESHOLD = int(os.environ.get('INVENTORY_AUTO_RESOLVE_THRESHOLD', '3'))  # Minimum "ya no está" reports to auto-resolve
    
    # Admin user configuration (for initial setup only)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@tarragoneta.org')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', None)  # Must be set in production, defaults to None for security

class DevelopmentConfig(Config):
    """Development configuration"""
    ENV = 'development'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')

class ProductionConfig(Config):
    """Production configuration"""
    ENV = 'production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')

# Default to development
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

