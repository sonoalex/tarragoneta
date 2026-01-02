"""
Rate limiting configuration for Flask-Security-Too endpoints and other routes
"""
from flask import current_app


def apply_security_rate_limits(app, limiter):
    """
    Apply rate limits to Flask-Security-Too endpoints after they're registered.
    
    Args:
        app: Flask application instance
        limiter: Flask-Limiter instance
    """
    # Create shared limits that will be applied to the endpoints
    forgot_password_limit = limiter.shared_limit("5 per hour", scope="forgot_password", methods=["POST"])
    login_limit = limiter.shared_limit("10 per hour", scope="login", methods=["POST"])
    
    # Apply limits to Flask-Security-Too views after they're registered
    # Flask-Security-Too registers views during init_app, so we apply limits after
    with app.app_context():
        # Apply rate limit to forgot_password view function
        if hasattr(app, 'view_functions') and 'security.forgot_password' in app.view_functions:
            original_view = app.view_functions['security.forgot_password']
            app.view_functions['security.forgot_password'] = forgot_password_limit(original_view)
            app.logger.info('Rate limit applied to security.forgot_password: 5 per hour')
        
        # Apply rate limit to login view function
        if hasattr(app, 'view_functions') and 'security.login' in app.view_functions:
            original_view = app.view_functions['security.login']
            app.view_functions['security.login'] = login_limit(original_view)
            app.logger.info('Rate limit applied to security.login: 10 per hour')
        
        # Apply rate limit to contact form
        if hasattr(app, 'view_functions') and 'main.contact' in app.view_functions:
            contact_limit = limiter.shared_limit("5 per hour", scope="contact", methods=["POST"])
            original_view = app.view_functions['main.contact']
            app.view_functions['main.contact'] = contact_limit(original_view)
            app.logger.info('Rate limit applied to main.contact: 5 per hour')

