import os
from flask import Flask
from app.config import config
from app.extensions import init_extensions
from app.routes import main, initiatives, admin, donations, inventory
from app.forms import ExtendedRegisterForm
from flask_security.signals import user_registered
from app.core import register_cli_commands, register_context_processors, register_error_handlers, setup_logging

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
    # Use static/uploads in both local and production
    # In Railway, mount the volume directly at static/uploads
    upload_folder = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    
    # Initialize extensions
    init_extensions(app)
    
    # Initialize Celery
    from app.celery_app import make_celery
    from app.tasks.email_tasks import init_tasks
    celery = make_celery(app)
    app.celery = celery
    
    # Register Celery tasks
    send_email_task = init_tasks(celery)
    app.send_email_task = send_email_task
    
    # Setup Flask-Security with custom form
    from app.extensions import user_datastore, security
    security.init_app(app, user_datastore, register_form=ExtendedRegisterForm)
    
    # Hook to save username on registration
    @user_registered.connect_via(app)
    def on_user_registered(sender, user, form_data, **kwargs):
        """Save username and assign default 'user' role when user registers"""
        from app.extensions import db, user_datastore
        from app.models import Role
        
        # Save username if provided
        if 'username' in form_data:
            user.username = form_data['username']
        
        # Assign default 'user' role if user doesn't have any roles
        if not user.roles:
            user_role = Role.query.filter_by(name='user').first()
            if user_role:
                user_datastore.add_role_to_user(user, user_role)
                app.logger.info(f'Assigned default "user" role to {user.email}')
            else:
                app.logger.warning('Default "user" role not found. User registered without roles.')
        
        db.session.commit()
        
        # Send welcome email
        try:
            from app.services.email_service import EmailService
            EmailService.send_welcome_email(user)
        except Exception as e:
            app.logger.error(f'Error sending welcome email: {str(e)}', exc_info=True)
    
    # Register blueprints
    app.register_blueprint(main.bp)
    app.register_blueprint(initiatives.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(donations.bp)
    app.register_blueprint(inventory.bp)
    from app.routes import analytics
    app.register_blueprint(analytics.bp)
    app.register_blueprint(analytics.bp_public)
    
    # Register CLI commands
    register_cli_commands(app)
    
    # Register context processors
    register_context_processors(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Profile route (simple, can be moved to auth blueprint later)
    from flask_security import login_required, current_user
    from app.models import InventoryItem, Initiative, Comment, ReportPurchase
    @app.route('/profile')
    @login_required
    def profile():
        from flask import render_template
        from datetime import datetime, timedelta
        
        # Get user statistics
        reported_items = InventoryItem.query.filter_by(reporter_id=current_user.id).all()
        participated = current_user.participated_initiatives.all()
        created = current_user.created_initiatives.all()
        comments = Comment.query.filter_by(user_id=current_user.id).order_by(Comment.created_at.desc()).limit(10).all()
        report_purchases = ReportPurchase.query.filter_by(user_id=current_user.id, status='completed').order_by(ReportPurchase.completed_at.desc()).limit(5).all()
        
        # Calculate statistics
        stats = {
            'reported_items': len(reported_items),
            'approved_items': len([item for item in reported_items if item.status == 'approved']),
            'active_items': len([item for item in reported_items if item.status == 'active']),
            'resolved_items': len([item for item in reported_items if item.status == 'resolved']),
            'created_initiatives': len(created),
            'participated_initiatives': len(participated),
            'comments': len(comments),
            'report_purchases': len(report_purchases),
            'total_contributions': len(reported_items) + len(created) + len(participated) + len(comments)
        }
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_items = InventoryItem.query.filter(
            InventoryItem.reporter_id == current_user.id,
            InventoryItem.created_at >= thirty_days_ago
        ).order_by(InventoryItem.created_at.desc()).limit(5).all()
        
        recent_initiatives = Initiative.query.filter(
            Initiative.creator_id == current_user.id,
            Initiative.created_at >= thirty_days_ago
        ).order_by(Initiative.created_at.desc()).limit(5).all()
        
        return render_template('profile.html', 
                             participated=participated, 
                             created=created,
                             reported_items=reported_items[:10],  # Last 10 reported items
                             recent_items=recent_items,
                             recent_initiatives=recent_initiatives,
                             comments=comments,
                             report_purchases=report_purchases,
                             stats=stats)
    
    # Configure logging
    setup_logging(app)
    
    return app

