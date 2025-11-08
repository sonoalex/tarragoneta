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
        from flask_babel import get_translations
        with app.app_context():
            # Test if translations load
            ca_translations = get_translations('ca')
            es_translations = get_translations('es')
            app.logger.info(f"Translations loaded - CA: {ca_translations is not None}, ES: {es_translations is not None}")
    except Exception as e:
        app.logger.warning(f"Could not verify translations: {e}")
    
    # Initialize Flask-Security (needs models)
    from app.models import User, Role
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    # Security will be initialized in create_app with custom form
    # Don't init here, let create_app do it with the custom form

