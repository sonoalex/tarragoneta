from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel
from flask_security import Security, SQLAlchemyUserDatastore

# Initialize extensions (will be initialized in app factory)
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
babel = Babel()
security = Security()

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
    babel.init_app(app, locale_selector=get_locale)
    
    # Verify translations are available
    try:
        import os
        translations_dir = app.config.get('BABEL_TRANSLATION_DIRECTORIES', 'babel/translations')
        ca_mo = os.path.join(translations_dir, 'ca', 'LC_MESSAGES', 'messages.mo')
        es_mo = os.path.join(translations_dir, 'es', 'LC_MESSAGES', 'messages.mo')
        ca_exists = os.path.exists(ca_mo)
        es_exists = os.path.exists(es_mo)
        app.logger.info(f"Translations files - CA: {ca_exists}, ES: {es_exists}")
        if ca_exists and es_exists:
            ca_size = os.path.getsize(ca_mo)
            es_size = os.path.getsize(es_mo)
            app.logger.info(f"Translation file sizes - CA: {ca_size} bytes, ES: {es_size} bytes")
    except Exception as e:
        app.logger.warning(f"Could not verify translations: {e}")
    
    # Initialize Flask-Security (needs models)
    from app.models import User, Role
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    # Security will be initialized in create_app with custom form
    # Don't init here, let create_app do it with the custom form

