"""Custom decorators for route protection"""
from functools import wraps
from flask import abort
from flask_security import current_user


def section_responsible_required(f):
    """Decorador que permite admin o responsables de sección"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        
        # Admin tiene acceso total
        if current_user.has_role('admin'):
            return f(*args, **kwargs)
        
        # Responsable de sección solo si tiene el rol
        if current_user.has_role('section_responsible'):
            return f(*args, **kwargs)
        
        abort(403)
    return decorated_function

