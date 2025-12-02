import os
import re
from flask import session
from PIL import Image
import bleach
from app.extensions import db
from app.config import Config

ALLOWED_EXTENSIONS = Config.ALLOWED_EXTENSIONS

def get_locale():
    """Language selector function for Babel - returns locale string"""
    from flask import has_request_context, session
    
    if has_request_context() and 'language' in session:
        lang = session['language']
        # Ensure it's a valid locale
        if lang in ['ca', 'es']:
            return lang
    # Default to Catalan
    return 'ca'

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def optimize_image(file_path):
    """Optimize uploaded images"""
    try:
        img = Image.open(file_path)
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        
        # Resize if too large
        max_size = (1200, 800)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save optimized image
        img.save(file_path, 'JPEG', quality=85, optimize=True)
        return True
    except Exception as e:
        print(f"Error optimizing image: {e}")
        return False

def sanitize_html(text):
    """Sanitize user input to prevent XSS"""
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'a']
    allowed_attributes = {'a': ['href', 'title']}
    return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)

def get_category_name(category_key):
    """Get translated category name"""
    from flask_babel import gettext as _
    category_names = {
        'limpieza': _('Cleaning'),
        'reciclaje': _('Recycling'),
        'espacios_verdes': _('Green Spaces'),
        'movilidad': _('Sustainable Mobility'),
        'educacion': _('Environmental Education'),
        'cultura': _('Culture and Civics'),
        'social': _('Social Action'),
        'basura_desbordada': _('Brossa Desbordada'),
        'vertidos': _('Dumping')
    }
    return category_names.get(category_key, category_key)

def get_inventory_category_name(category, subcategory=None):
    """Get translated inventory category and subcategory names"""
    from flask_babel import gettext as _
    
    # Main categories (en catalán por defecto)
    main_categories = {
        'palomas': _('Coloms'),
        'basura': _('Brossa')
    }
    
    # Subcategories (en catalán por defecto)
    subcategories = {
        'excremento': _('Excrement'),
        'nido': _('Niu'),
        'plumas': _('Plomes'),
        'basura_desbordada': _('Brossa Desbordada'),
        'vertidos': _('Abocaments'),
        'otro': _('Altres')
    }
    
    main_name = main_categories.get(category, category)
    if subcategory:
        sub_name = subcategories.get(subcategory, subcategory)
        return f"{main_name} → {sub_name}"
    return main_name

def get_inventory_icon(category, subcategory=None):
    """
    Get Font Awesome icon class for inventory category/subcategory.
    Returns a tuple of (icon_class, color_class) for use in templates.
    
    Args:
        category: Main category (e.g., 'palomas', 'basura')
        subcategory: Optional subcategory (e.g., 'nido', 'excremento', 'plumas', 'basura_desbordada', 'vertidos')
    
    Returns:
        tuple: (icon_class, color_class) e.g., ('fa-dove', 'text-primary')
    """
    # Mapping: (category, subcategory) -> (icon_class, color_class)
    icon_mapping = {
        # Palomas
        ('palomas', 'nido'): ('fa-home', 'text-primary'),
        ('palomas', 'excremento'): ('fa-biohazard', 'text-danger'),
        ('palomas', 'plumas'): ('fa-feather', 'text-info'),
        ('palomas', None): ('fa-dove', 'text-primary'),
        ('palomas', 'otro'): ('fa-dove', 'text-primary'),
        
        # Basura
        ('basura', 'basura_desbordada'): ('fa-trash-alt', 'text-warning'),
        ('basura', 'vertidos'): ('fa-tint', 'text-danger'),
        ('basura', None): ('fa-trash', 'text-secondary'),
        ('basura', 'otro'): ('fa-trash', 'text-secondary'),
    }
    
    # Try to get icon for specific category+subcategory combination
    key = (category, subcategory)
    if key in icon_mapping:
        return icon_mapping[key]
    
    # Fallback to category only
    key = (category, None)
    if key in icon_mapping:
        return icon_mapping[key]
    
    # Default fallback
    return ('fa-circle', 'text-secondary')

def generate_slug(title):
    """Generate a URL-friendly slug from title"""
    if not title:
        return 'untitled'
    # Convert to lowercase
    slug = title.lower()
    # Remove emojis and special unicode characters
    slug = re.sub(r'[^\w\s-]', '', slug)
    # Replace spaces and multiple hyphens with single hyphen
    slug = re.sub(r'[-\s]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Ensure slug is not empty
    if not slug:
        slug = 'untitled'
    return slug

# Mapeo entre valores en catalán (URLs) y valores técnicos (BD)
CATEGORY_URL_TO_DB = {
    'coloms': 'palomas',
    'brossa': 'basura',
}

CATEGORY_DB_TO_URL = {v: k for k, v in CATEGORY_URL_TO_DB.items()}

SUBCATEGORY_URL_TO_DB = {
    'niu': 'nido',
    'excrement': 'excremento',
    'plomes': 'plumas',
    'brossa_desbordada': 'basura_desbordada',
    'abocaments': 'vertidos',
    'altres': 'otro',
}

SUBCATEGORY_DB_TO_URL = {v: k for k, v in SUBCATEGORY_URL_TO_DB.items()}

def normalize_category_from_url(category_url):
    """Convierte el valor de categoría de la URL (catalán) al valor técnico de BD"""
    if not category_url:
        return None
    return CATEGORY_URL_TO_DB.get(category_url, category_url)

def normalize_subcategory_from_url(subcategory_url):
    """Convierte el valor de subcategoría de la URL (catalán) al valor técnico de BD"""
    if not subcategory_url:
        return None
    return SUBCATEGORY_URL_TO_DB.get(subcategory_url, subcategory_url)

def category_to_url(category_db):
    """Convierte el valor técnico de categoría a valor de URL (catalán)"""
    if not category_db:
        return None
    return CATEGORY_DB_TO_URL.get(category_db, category_db)

def subcategory_to_url(subcategory_db):
    """Convierte el valor técnico de subcategoría a valor de URL (catalán)"""
    if not subcategory_db:
        return None
    return SUBCATEGORY_DB_TO_URL.get(subcategory_db, subcategory_db)

