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

def calculate_distance_km(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two GPS coordinates in kilometers using Haversine formula.
    Returns distance in kilometers.
    """
    from math import radians, sin, cos, sqrt, atan2
    
    # Convert to radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    # Earth radius in kilometers
    R = 6371.0
    
    return R * c

def extract_gps_from_image(file_path):
    """
    Extract GPS coordinates from image EXIF data.
    Returns (latitude, longitude) tuple or (None, None) if not found.
    """
    try:
        from PIL.ExifTags import TAGS, GPSTAGS
        
        img = Image.open(file_path)
        exif_data = img._getexif()
        
        if exif_data is None:
            return None, None
        
        # Find GPS info in EXIF
        gps_info = None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'GPSInfo':
                gps_info = value
                break
        
        if gps_info is None:
            return None, None
        
        # Extract GPS coordinates
        gps_data = {}
        for key, value in gps_info.items():
            tag = GPSTAGS.get(key, key)
            gps_data[tag] = value
        
        # Get latitude
        lat_ref = gps_data.get('GPSLatitudeRef', 'N')
        lat = gps_data.get('GPSLatitude')
        
        # Get longitude
        lon_ref = gps_data.get('GPSLongitudeRef', 'E')
        lon = gps_data.get('GPSLongitude')
        
        if lat is None or lon is None:
            return None, None
        
        # Convert to decimal degrees
        # lat/lon are tuples: (degrees, minutes, seconds)
        latitude = float(lat[0]) + (float(lat[1]) / 60.0) + (float(lat[2]) / 3600.0)
        if lat_ref == 'S':
            latitude = -latitude
        
        longitude = float(lon[0]) + (float(lon[1]) / 60.0) + (float(lon[2]) / 3600.0)
        if lon_ref == 'W':
            longitude = -longitude
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"✅ GPS extraído de imagen: lat={latitude}, lng={longitude}")
        return latitude, longitude
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"❌ Error extrayendo GPS de imagen: {e}")
        return None, None

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

def generate_image_sizes(original_path, base_filename):
    """
    Generate multiple sizes of an image: thumbnail, medium, and large.
    Returns a dict with paths for each size.
    
    Args:
        original_path: Full path to the original image
        base_filename: Base filename (without extension) to use for generated sizes
    
    Returns:
        dict with keys: 'thumbnail', 'medium', 'large', 'original'
        Each value is the filename (not full path) for that size
    """
    try:
        img = Image.open(original_path)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        
        # Get directory and base name
        upload_dir = os.path.dirname(original_path)
        base_name, ext = os.path.splitext(base_filename)
        if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png']:
            ext = '.jpg'
        
        # Define sizes
        sizes = {
            'thumbnail': (150, 150),  # Square thumbnail for map markers
            'medium': (800, 600),     # Medium for popups and lists
            'large': (1200, 800),     # Large for detail views
        }
        
        generated_files = {}
        
        # Generate each size
        for size_name, (max_width, max_height) in sizes.items():
            # Create a copy for resizing
            resized_img = img.copy()
            
            # Calculate aspect ratio preserving dimensions
            img_width, img_height = resized_img.size
            aspect_ratio = img_width / img_height
            
            if aspect_ratio > max_width / max_height:
                # Image is wider
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:
                # Image is taller
                new_height = max_height
                new_width = int(max_height * aspect_ratio)
            
            # Resize with high-quality resampling
            resized_img = resized_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Generate filename
            size_filename = f"{base_name}_{size_name}{ext}"
            size_path = os.path.join(upload_dir, size_filename)
            
            # Save with quality optimization
            quality = 85 if size_name == 'large' else 90
            resized_img.save(size_path, 'JPEG', quality=quality, optimize=True)
            
            generated_files[size_name] = size_filename
        
        # Save optimized original as 'large' (or keep original if smaller)
        # The 'large' version is what we'll use as the main image
        original_img = img.copy()
        if original_img.size[0] > sizes['large'][0] or original_img.size[1] > sizes['large'][1]:
            # Original is larger than 'large', resize it
            original_img.thumbnail(sizes['large'], Image.Resampling.LANCZOS)
        
        # Save as 'large' version (this will be the main image_path stored in DB)
        large_filename = f"{base_name}_large{ext}"
        large_path = os.path.join(upload_dir, large_filename)
        original_img.save(large_path, 'JPEG', quality=85, optimize=True)
        generated_files['large'] = large_filename
        
        # Remove the original file (we now have large, medium, thumbnail)
        if os.path.exists(original_path):
            os.remove(original_path)
        
        # The 'original' key points to 'large' (which is the main optimized image)
        generated_files['original'] = large_filename
        
        return generated_files
        
    except Exception as e:
        print(f"Error generating image sizes: {e}")
        # Return original filename if generation fails
        return {'original': base_filename, 'thumbnail': base_filename, 'medium': base_filename, 'large': base_filename}

def get_image_path(image_filename, size='large'):
    """
    Get the image path for a specific size.
    
    Args:
        image_filename: The image filename (could be base or already have a suffix like '_large.jpg')
        size: One of 'thumbnail', 'medium', 'large', or 'original' (original = large)
    
    Returns:
        The filename for the requested size
    """
    if not image_filename:
        return None
    
    # If size is 'original', use 'large' (they're the same)
    if size == 'original':
        size = 'large'
    
    # If filename already has a size suffix, remove it first
    import re
    base_name = re.sub(r'_(thumbnail|medium|large)(\.[^.]+)$', r'\2', image_filename)
    base_name, ext = os.path.splitext(base_name)
    if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png']:
        ext = '.jpg'
    
    # Construct filename with size suffix
    return f"{base_name}_{size}{ext}"


def get_image_url(image_filename, size='large'):
    """
    Get URL for an image stored via the configured storage provider.
    Falls back to original filename if sized version is not found.
    """
    from flask import current_app
    from app.storage import get_storage
    import os

    if not image_filename:
        return None

    sized_filename = get_image_path(image_filename, size)

    storage = get_storage()
    provider = current_app.config.get('STORAGE_PROVIDER', 'local').lower()
    
    current_app.logger.debug(
        f'🖼️ get_image_url: filename={image_filename}, size={size}, '
        f'sized_filename={sized_filename}, provider={provider}'
    )

    if provider == 's3':
        key_to_use = sized_filename
        current_app.logger.debug(f'☁️ Using S3, key={key_to_use}')
    else:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
        sized_path = os.path.join(upload_folder, sized_filename)
        key_to_use = sized_filename if os.path.exists(sized_path) else image_filename
        current_app.logger.debug(
            f'📁 Using local storage, key={key_to_use}, '
            f'sized_path_exists={os.path.exists(sized_path)}'
        )

    try:
        url = storage.url_for(key_to_use)
        current_app.logger.debug(f'✅ get_image_url: Returning URL={url}')
        return url
    except Exception as e:
        current_app.logger.warning(f'⚠️ get_image_url: Error with key {key_to_use}: {e}')
        try:
            url = storage.url_for(image_filename)
            current_app.logger.debug(f'✅ get_image_url: Fallback URL={url}')
            return url
        except Exception as e2:
            current_app.logger.error(f'❌ get_image_url: Both attempts failed: {e2}')
            return None

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
        'escombreries_desbordades': _('Escombreries Desbordades'),
        'vertidos': _('Dumping')
    }
    return category_names.get(category_key, category_key)

def get_inventory_category_name(category, subcategory=None):
    """Get translated inventory category and subcategory names"""
    from flask_babel import gettext as _
    
    # Main categories (en catalán por defecto)
    # Las traducciones se evalúan en el momento de la llamada, no en la definición
    main_categories = {
        'palomas': lambda: _('Coloms'),
        'basura': lambda: _('Brossa'),
        'perros': lambda: _('Gossos'),
        'material_deteriorat': lambda: _('Material Deteriorat'),
        'bruticia': lambda: _('Brutícia'),
        'mobiliari_urba': lambda: _('Mobiliari Urbà'),
        'vegetacio': lambda: _('Vegetació'),
        'infraestructura': lambda: _('Infraestructura')
    }
    
    # Subcategories (en catalán por defecto)
    subcategories = {
        # Palomas
        'excremento': lambda: _('Excrement'),
        'nido': lambda: _('Niu'),
        'plumas': lambda: _('Plomes'),
        # Basura
        'escombreries_desbordades': lambda: _('Escombreries Desbordades'),
        'basura_desbordada': lambda: _('Escombreries Desbordades'),  # Alias para compatibilidad con datos antiguos
        'vertidos': lambda: _('Abocaments'),
        # Perros
        'excrements': lambda: _('Excrements'),
        'pixades': lambda: _('Pixades'),
        # Material Deteriorat
        'faroles': lambda: _('Faroles'),
        'bancs': lambda: _('Bancs'),
        'senyals': lambda: _('Senyals'),
        'paviment': lambda: _('Paviment'),
        # Brutícia
        'terra': lambda: _('Terra'),
        'fulles': lambda: _('Fulles'),
        'grafit': lambda: _('Grafit'),
        # Mobiliari Urbà
        'papereres': lambda: _('Papereres'),
        'parades': lambda: _('Parades'),
        # Vegetació
        'arbres': lambda: _('Arbres'),
        'arbustos': lambda: _('Arbustos'),
        'gespa': lambda: _('Gespa'),
        # Infraestructura
        'carreteres': lambda: _('Carreteres'),
        'voreres': lambda: _('Voreres'),
        'enllumenat': lambda: _('Enllumenat'),
        # General
        'otro': lambda: _('Altres')
    }
    
    # Obtener el nombre traducido llamando a la función lambda
    get_main_name = main_categories.get(category)
    main_name = get_main_name() if get_main_name else category
    
    if subcategory:
        get_sub_name = subcategories.get(subcategory)
        sub_name = get_sub_name() if get_sub_name else subcategory
        return f"{main_name} → {sub_name}"
    return main_name

def get_inventory_subcategory_name(subcategory):
    """Get translated subcategory name only"""
    from flask_babel import gettext as _
    
    subcategories = {
        # Palomas
        'excremento': lambda: _('Excrement'),
        'nido': lambda: _('Niu'),
        'plumas': lambda: _('Plomes'),
        # Basura
        'escombreries_desbordades': lambda: _('Escombreries Desbordades'),
        'basura_desbordada': lambda: _('Escombreries Desbordades'),  # Alias para compatibilidad con datos antiguos
        'vertidos': lambda: _('Abocaments'),
        # Perros
        'excrements': lambda: _('Excrements'),
        'pixades': lambda: _('Pixades'),
        # Material Deteriorat
        'faroles': lambda: _('Faroles'),
        'bancs': lambda: _('Bancs'),
        'senyals': lambda: _('Senyals'),
        'paviment': lambda: _('Paviment'),
        # Brutícia
        'terra': lambda: _('Terra'),
        'fulles': lambda: _('Fulles'),
        'grafit': lambda: _('Grafit'),
        # Mobiliari Urbà
        'papereres': lambda: _('Papereres'),
        'parades': lambda: _('Parades'),
        # Vegetació
        'arbres': lambda: _('Arbres'),
        'arbustos': lambda: _('Arbustos'),
        'gespa': lambda: _('Gespa'),
        # Infraestructura
        'carreteres': lambda: _('Carreteres'),
        'voreres': lambda: _('Voreres'),
        'enllumenat': lambda: _('Enllumenat'),
        # General
        'otro': lambda: _('Altres')
    }
    
    get_sub_name = subcategories.get(subcategory)
    return get_sub_name() if get_sub_name else subcategory

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
        ('basura', 'escombreries_desbordades'): ('fa-trash-alt', 'text-warning'),
        ('basura', 'vertidos'): ('fa-tint', 'text-danger'),
        ('basura', None): ('fa-trash', 'text-secondary'),
        ('basura', 'otro'): ('fa-trash', 'text-secondary'),
        
        # Perros
        ('perros', 'excrements'): ('fa-poop', 'text-danger'),
        ('perros', 'pixades'): ('fa-tint', 'text-warning'),
        ('perros', None): ('fa-dog', 'text-secondary'),
        ('perros', 'otro'): ('fa-dog', 'text-secondary'),
        
        # Material Deteriorat
        ('material_deteriorat', 'faroles'): ('fa-lightbulb', 'text-warning'),
        ('material_deteriorat', 'bancs'): ('fa-chair', 'text-info'),
        ('material_deteriorat', 'senyals'): ('fa-sign', 'text-warning'),
        ('material_deteriorat', 'paviment'): ('fa-road', 'text-danger'),
        ('material_deteriorat', None): ('fa-tools', 'text-secondary'),
        ('material_deteriorat', 'otro'): ('fa-tools', 'text-secondary'),
        
        # Brutícia
        ('bruticia', 'terra'): ('fa-mountain', 'text-warning'),
        ('bruticia', 'fulles'): ('fa-leaf', 'text-success'),
        ('bruticia', 'grafit'): ('fa-spray-can', 'text-danger'),
        ('bruticia', None): ('fa-broom', 'text-secondary'),
        ('bruticia', 'otro'): ('fa-broom', 'text-secondary'),
        
        # Mobiliari Urbà
        ('mobiliari_urba', 'papereres'): ('fa-trash', 'text-info'),
        ('mobiliari_urba', 'parades'): ('fa-bus', 'text-primary'),
        ('mobiliari_urba', 'bancs'): ('fa-chair', 'text-info'),
        ('mobiliari_urba', None): ('fa-city', 'text-secondary'),
        ('mobiliari_urba', 'otro'): ('fa-city', 'text-secondary'),
        
        # Vegetació
        ('vegetacio', 'arbres'): ('fa-tree', 'text-success'),
        ('vegetacio', 'arbustos'): ('fa-seedling', 'text-success'),
        ('vegetacio', 'gespa'): ('fa-grass', 'text-success'),
        ('vegetacio', None): ('fa-tree', 'text-success'),
        ('vegetacio', 'otro'): ('fa-tree', 'text-success'),
        
        # Infraestructura
        ('infraestructura', 'carreteres'): ('fa-road', 'text-danger'),
        ('infraestructura', 'voreres'): ('fa-walking', 'text-info'),
        ('infraestructura', 'enllumenat'): ('fa-lightbulb', 'text-warning'),
        ('infraestructura', None): ('fa-building', 'text-secondary'),
        ('infraestructura', 'otro'): ('fa-building', 'text-secondary'),
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
    'gossos': 'perros',
    'material_deteriorat': 'material_deteriorat',
    'bruticia': 'bruticia',
    'mobiliari_urba': 'mobiliari_urba',
    'vegetacio': 'vegetacio',
    'infraestructura': 'infraestructura',
}

CATEGORY_DB_TO_URL = {v: k for k, v in CATEGORY_URL_TO_DB.items()}

SUBCATEGORY_URL_TO_DB = {
    # Palomas
    'niu': 'nido',
    'excrement': 'excremento',
    'plomes': 'plumas',
    # Basura
    'escombreries_desbordades': 'escombreries_desbordades',
    'abocaments': 'vertidos',
    # Perros
    'excrements': 'excrements',
    'pixades': 'pixades',
    # Material Deteriorat
    'faroles': 'faroles',
    'bancs': 'bancs',
    'senyals': 'senyals',
    'paviment': 'paviment',
    # Brutícia
    'terra': 'terra',
    'fulles': 'fulles',
    'grafit': 'grafit',
    # Mobiliari Urbà
    'papereres': 'papereres',
    'parades': 'parades',
    # Vegetació
    'arbres': 'arbres',
    'arbustos': 'arbustos',
    'gespa': 'gespa',
    # Infraestructura
    'carreteres': 'carreteres',
    'voreres': 'voreres',
    'enllumenat': 'enllumenat',
    # General
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

