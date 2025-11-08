import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, session
from app.config import config
from app.extensions import init_extensions
from app.routes import main, initiatives, admin, donations, inventory
from app.forms import ExtendedRegisterForm
from app.utils import get_category_name
from flask_security.signals import user_registered
from flask_babel import gettext as _

def create_app(config_name=None):
    """Application factory pattern"""
    # Get the root directory (parent of app/)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(root_dir, 'templates')
    static_dir = os.path.join(root_dir, 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # Load configuration
    if config_name is None:
        # Check if we're in production (Railway sets RAILWAY_ENVIRONMENT)
        if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('FLASK_ENV') == 'production':
            config_name = 'production'
        else:
            config_name = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config.get(config_name, config['default']))
    
    # Configure session to be permanent
    from datetime import timedelta
    app.permanent_session_lifetime = timedelta(days=1)
    
    # Create directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    
    # Initialize extensions
    init_extensions(app)
    
    # Setup Flask-Security with custom form
    from app.extensions import user_datastore, security
    security.init_app(app, user_datastore, register_form=ExtendedRegisterForm)
    
    # Hook to save username on registration
    @user_registered.connect_via(app)
    def on_user_registered(sender, user, confirm_token, form_data):
        """Save username when user registers"""
        if 'username' in form_data:
            user.username = form_data['username']
            from app.extensions import db
            db.session.commit()
    
    # Register blueprints
    app.register_blueprint(main.bp)
    app.register_blueprint(initiatives.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(donations.bp)
    app.register_blueprint(inventory.bp)
    
    # Context processor for templates
    @app.context_processor
    def inject_gettext():
        def current_locale():
            """Get current locale string for templates"""
            try:
                from flask_babel import get_locale as babel_get_locale
                locale = babel_get_locale()
                return str(locale) if locale else 'ca'
            except:
                return session.get('language', 'ca')
        
        return dict(_=_, get_locale=current_locale, get_category_name=get_category_name)
    
    # Error handlers
    from flask import render_template, request
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f'404 error: {request.url}')
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from app.extensions import db
        db.session.rollback()
        app.logger.error(f'500 error: {str(error)}', exc_info=True)
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        app.logger.warning(f'403 error: {request.url}')
        return render_template('errors/403.html'), 403
    
    # Profile route (simple, can be moved to auth blueprint later)
    from flask_security import login_required, current_user
    @app.route('/profile')
    @login_required
    def profile():
        from flask import render_template
        participated = current_user.participated_initiatives.all()
        created = current_user.created_initiatives.all()
        return render_template('profile.html', participated=participated, created=created)
    
    # Configure logging
    if not app.debug:
        # Production logging - log to file
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/tarragoneta.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Tarragoneta startup')
    else:
        # Development logging - log to console with more detail
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)
        app.logger.info('Tarragoneta startup (DEBUG mode)')
    
    # Log configuration on startup
    app.logger.info(f"Environment: {app.config['ENV']}")
    app.logger.info(f"Debug mode: {app.config['DEBUG']}")
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    # Mask password in logs
    if '@' in db_uri:
        # Hide password from connection string
        import re
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
    
    # Warn if using SQLite in production (but allow it for staging)
    if app.config['ENV'] == 'production' and 'sqlite' in db_uri.lower():
        app.logger.warning("⚠️  Using SQLite in production (staging mode).")
        app.logger.info("   This is OK for testing, but data will be lost on each deployment.")
        app.logger.info("   For production, add PostgreSQL in Railway.")
    
    return app

