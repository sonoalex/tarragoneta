"""
Context processors for templates
"""
from flask import session
from flask_babel import gettext as _
from app.utils import (
    get_category_name,
    get_inventory_category_name,
    get_inventory_subcategory_name,
    get_inventory_icon,
    category_to_url,
    subcategory_to_url,
    calculate_distance_km,
    get_image_path,
    get_image_url,
)


def register_context_processors(app):
    """Register context processors for templates"""
    @app.context_processor
    def inject_gettext():
        def current_locale():
            """Get current locale string for templates"""
            try:
                from flask_babel import get_locale as babel_get_locale
                locale = babel_get_locale()
                locale_str = str(locale) if locale else 'ca'
                return locale_str
            except Exception as e:
                app.logger.warning(f"Error in current_locale(): {e}")
                return session.get('language', 'ca')
        
        # Get pending initiatives count for admin/moderator
        pending_count = 0
        try:
            from flask_security import current_user
            from app.models import RoleEnum
            if current_user.is_authenticated and (current_user.has_role(RoleEnum.ADMIN.value) or current_user.has_role(RoleEnum.MODERATOR.value)):
                from app.models import Initiative
                pending_count = Initiative.query.filter(Initiative.status == 'pending').count()
        except Exception:
            pass  # Ignore errors in context processor
        
        from flask import current_app
        
        return dict(
            _=_,
            get_locale=current_locale,
            get_category_name=get_category_name,
            get_inventory_category_name=get_inventory_category_name,
            get_inventory_subcategory_name=get_inventory_subcategory_name,
            get_inventory_icon=get_inventory_icon,
            category_to_url=category_to_url,
            subcategory_to_url=subcategory_to_url,
            calculate_distance_km=calculate_distance_km,
            get_image_url=get_image_url,
            get_image_path=get_image_path,
            pending_initiatives_count=pending_count,
            config=current_app.config
        )

