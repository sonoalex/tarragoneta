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

# Email providers are initialized on-demand via app/providers/__init__.py

# Will be set after models are imported
user_datastore = None

def init_extensions(app):
    """Initialize Flask extensions"""
    global user_datastore
    
    # Initialize SQLAlchemy with engine options if configured
    engine_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
    db.init_app(app)
    # Engine options are automatically applied via SQLALCHEMY_ENGINE_OPTIONS in config
    
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
    # Flask-Mail handles SMTP connections internally
    # Timeout is handled at the thread level in SMTPEmailProvider
    mail.init_app(app)
    
    # Initialize Dependency Injection Container
    from app.container import get_container
    from app.providers.base import EmailProvider
    from app.providers.smtp_provider import SMTPEmailProvider
    from app.providers.console_provider import ConsoleEmailProvider
    
    container = get_container()
    
    # Select email provider based on configuration
    provider_name = app.config.get('EMAIL_PROVIDER', 'smtp').lower()
    selected_provider = None
    
    app.logger.info(f'Email provider configuration: EMAIL_PROVIDER={provider_name}')
    
    # Select provider based on configuration
    if provider_name == 'smtp':
        provider = SMTPEmailProvider()
        if provider.is_available(app=app):
            selected_provider = provider
            app.logger.info('SMTP provider selected')
        else:
            app.logger.warning('SMTP provider requested but not available, falling back to console')
            selected_provider = ConsoleEmailProvider()
    
    elif provider_name == 'console':
        selected_provider = ConsoleEmailProvider()
        app.logger.info('Console provider selected')
    
    else:
        # Unknown provider, default to SMTP, fallback to console
        app.logger.warning(f'Unknown email provider: {provider_name}, trying SMTP...')
        provider = SMTPEmailProvider()
        if provider.is_available(app=app):
            selected_provider = provider
            app.logger.info('Using SMTP provider (fallback)')
        else:
            app.logger.warning('SMTP not available, using console provider')
            selected_provider = ConsoleEmailProvider()
    
    # Register the selected provider instance
    container.register_instance(
        'email_provider',
        selected_provider,
        service_type=EmailProvider
    )
    app.logger.info(f'Dependency Injection container initialized with {selected_provider.__class__.__name__}')
    
    # Initialize Flask-Security (needs models)
    from app.models import User, Role
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    # Security will be initialized in create_app with custom form
    # Don't init here, let create_app do it with the custom form

