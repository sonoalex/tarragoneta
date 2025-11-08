import os
import re
from flask import session
from PIL import Image
import bleach
from app.extensions import db
from app.config import Config

ALLOWED_EXTENSIONS = Config.ALLOWED_EXTENSIONS

def get_locale():
    """Language selector function for Babel - must return a Locale object or string"""
    from flask import has_request_context, session
    from babel import Locale
    
    if has_request_context() and 'language' in session:
        lang = session['language']
        # Ensure it's a valid locale
        if lang in ['ca', 'es']:
            try:
                # Return Locale object for better compatibility
                return Locale.parse(lang)
            except:
                # Fallback to string if Locale parsing fails
                return lang
    # Default to Catalan
    try:
        return Locale.parse('ca')
    except:
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
        'social': _('Social Action')
    }
    return category_names.get(category_key, category_key)

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

