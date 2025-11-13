from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel
from flask_security import Security, SQLAlchemyUserDatastore
from flask_mail import Mail

# Initialize extensions (will be initialized in app factory)
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
babel = Babel()
security = Security()
mail = Mail()

# Redis and RQ queue (initialized in init_extensions)
redis_conn = None
email_queue = None

# Will be set after models are imported
user_datastore = None

def init_extensions(app):
    """Initialize Flask extensions"""
    global user_datastore
    
    # Initialize SQLAlchemy with engine options if configured
    engine_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
    db.init_app(app)
    if engine_options:
        # Apply engine options to the database engine
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            # SQLite specific optimizations
            if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Initialize Babel with locale selector
    from app.utils import get_locale
    import os
    
    # Get absolute path to translations directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    translations_dir = os.path.join(root_dir, 'babel', 'translations')
    
    # Update config with absolute path
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = translations_dir
    
    babel.init_app(app, locale_selector=get_locale)
    
    # Initialize Flask-Mail
    mail.init_app(app)
    
    # Configure SMTP timeout if specified
    if app.config.get('MAIL_TIMEOUT'):
        # Flask-Mail uses smtplib internally, we need to patch it
        import smtplib
        original_smtp = smtplib.SMTP
        
        def patched_smtp(*args, **kwargs):
            # Add timeout to SMTP connection
            if 'timeout' not in kwargs:
                kwargs['timeout'] = app.config.get('MAIL_TIMEOUT', 10)
            return original_smtp(*args, **kwargs)
        
        # Only patch if not already patched
        if not hasattr(smtplib.SMTP, '_tarragoneta_patched'):
            smtplib.SMTP = patched_smtp
            smtplib.SMTP._tarragoneta_patched = True
    
    # Initialize Redis and RQ queue for background jobs
    global redis_conn, email_queue
    try:
        from redis import Redis
        from rq import Queue
        
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        # Don't use decode_responses=True for RQ - it handles serialization internally
        redis_conn = Redis.from_url(redis_url, decode_responses=False)
        # Test connection
        redis_conn.ping()
        email_queue = Queue('emails', connection=redis_conn)
        app.logger.info('Redis and email queue initialized successfully')
    except Exception as e:
        app.logger.warning(f'Redis not available, emails will be sent synchronously: {str(e)}')
        redis_conn = None
        email_queue = None
    
    # Initialize Flask-Security (needs models)
    from app.models import User, Role
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    # Security will be initialized in create_app with custom form
    # Don't init here, let create_app do it with the custom form

