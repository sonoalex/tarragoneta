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

def _convert_to_degrees(value):
    """
    Convierte coordenadas GPS (degrees, minutes, seconds) a decimal.
    Maneja tanto tuplas como objetos Rational de Pillow.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        def to_float(v):
            if hasattr(v, 'numerator') and hasattr(v, 'denominator'):
                return float(v.numerator) / float(v.denominator)
            return float(v)
        
        # Asegurar que tenemos una tupla/lista de 3 elementos
        if not isinstance(value, (tuple, list)) or len(value) < 1:
            raise ValueError(f"Invalid GPS coordinate format: {value}")
        
        degrees = to_float(value[0])
        minutes = to_float(value[1]) if len(value) > 1 else 0.0
        seconds = to_float(value[2]) if len(value) > 2 else 0.0
        
        return degrees + (minutes / 60.0) + (seconds / 3600.0)
        
    except (ValueError, TypeError, IndexError, AttributeError) as e:
        logger.error(f"Error converting GPS value {value}: {e}")
        raise


def _extract_gps_from_dict(gps_info, method):
    """
    Extrae coordenadas GPS de un diccionario GPS info.
    
    Args:
        gps_info: Diccionario con datos GPS
        method: Nombre del método usado (para logging)
    
    Returns:
        Tupla (latitud, longitud) o None si faltan datos
    """
    import logging
    from PIL.ExifTags import GPSTAGS
    
    logger = logging.getLogger(__name__)
    
    # Normalizar el diccionario usando GPSTAGS
    gps_data = {}
    for key, value in gps_info.items():
        decoded_key = GPSTAGS.get(key, key)
        gps_data[decoded_key] = value
    
    logger.debug(f"GPS data keys from {method}: {list(gps_data.keys())}")
    
    # Extraer componentes
    lat = gps_data.get('GPSLatitude')
    lat_ref = gps_data.get('GPSLatitudeRef', 'N')
    lon = gps_data.get('GPSLongitude')
    lon_ref = gps_data.get('GPSLongitudeRef', 'E')
        
    if lat is None or lon is None:
        logger.warning(f"Missing GPS coordinates in {method}: lat={lat}, lon={lon}")
        return None
    
    try:
        # Convertir a decimal
        latitude = _convert_to_degrees(lat)
        longitude = _convert_to_degrees(lon)
        
        # Aplicar hemisferios
        if lat_ref == 'S':
            latitude = -latitude
        if lon_ref == 'W':
            longitude = -longitude
        
        logger.info(f"✅ GPS extracted via {method}: ({latitude}, {longitude})")
        return latitude, longitude
        
    except Exception as e:
        logger.error(f"Error converting GPS coordinates from {method}: {e}")
        return None


def extract_gps_from_image(file_path):
    """
    Extrae coordenadas GPS de una imagen usando exifread (robusto para iOS).
    Si exifread falla, intenta con _getexif() de Pillow como fallback.
    
    Args:
        file_path: Ruta a la imagen
    
    Returns:
        Tupla (latitud, longitud) o (None, None) si no se encuentra
    """
    import logging
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    
    # Validar archivo
    path = Path(file_path)
    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return None, None
    
    logger.debug(f"Extracting GPS from image: {path.name}")
    
    # === MÉTODO 1: Usar exifread (robusto para iOS) ===
    try:
        import exifread
        
        # Abrir imagen en modo binario y procesar EXIF
        with open(file_path, 'rb') as img_file:
            tags = exifread.process_file(img_file, details=False)
            
            logger.debug(f"exifread returned {len(tags)} tags")
            
            # Extraer información GPS
            gps_latitude = tags.get("GPS GPSLatitude")
            gps_latitude_ref = tags.get("GPS GPSLatitudeRef")
            gps_longitude = tags.get("GPS GPSLongitude")
            gps_longitude_ref = tags.get("GPS GPSLongitudeRef")
            
            logger.debug(f"exifread GPS: lat={gps_latitude is not None}, lat_ref={gps_latitude_ref is not None}, lon={gps_longitude is not None}, lon_ref={gps_longitude_ref is not None}")
            
            # Verificar si tenemos toda la información GPS necesaria
            if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
                # Convertir coordenadas GPS a grados decimales
                def convert_to_degrees(value):
                    """Convierte un valor de exifread (Ratio) a grados decimales"""
                    # exifread devuelve objetos Ratio con .values que es una lista de Ratio
                    # Cada Ratio tiene .num (numerador) y .den (denominador)
                    d = float(value.values[0].num) / float(value.values[0].den)  # Degrees
                    m = float(value.values[1].num) / float(value.values[1].den)  # Minutes
                    s = float(value.values[2].num) / float(value.values[2].den)  # Seconds
                    
                    # Calcular grados decimales
                    return d + (m / 60.0) + (s / 3600.0)
                
                lat = convert_to_degrees(gps_latitude)
                lon = convert_to_degrees(gps_longitude)
                
                # Ajustar latitud y longitud según los valores de referencia
                # exifread devuelve objetos Ratio, necesitamos acceder a .values[0]
                if gps_latitude_ref.values[0] != 'N':
                    lat = -lat
                if gps_longitude_ref.values[0] != 'E':
                    lon = -lon
                
                logger.info(f"✅ GPS extracted via exifread: ({lat:.6f}, {lon:.6f})")
                return lat, lon
            else:
                # Log qué tags GPS están disponibles para debugging
                gps_tags = {k: v for k, v in tags.items() if k.startswith('GPS')}
                logger.debug(f"exifread: GPS data incomplete. Available GPS tags: {list(gps_tags.keys())}")
                
    except ImportError:
        logger.debug("exifread not available, trying Pillow _getexif()")
    except Exception as e:
        logger.debug(f"exifread failed: {e}, trying Pillow _getexif()")
    
    # === MÉTODO 2: Usar _getexif() de Pillow como fallback ===
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        
        image = Image.open(file_path)
        logger.debug(f"Image opened: {path.name}, format={image.format}, size={image.size}")
        
        # Verificar si hay datos EXIF
        exif_data = image._getexif()
        if exif_data is None:
            logger.warning(f"❌ {path.name} contains no exif data")
            return None, None
        
        logger.debug(f"Pillow _getexif() returned {len(exif_data)} tags")
        
        # Buscar GPSInfo en los tags EXIF
        gps_coords = {}
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag)
            if tag_name == "GPSInfo":
                logger.debug(f"✅ GPSInfo found at tag {tag}")
                # Extraer datos GPS del diccionario GPSInfo
                for key, val in value.items():
                    gps_tag_name = GPSTAGS.get(key)
                    logger.debug(f"GPS tag: {gps_tag_name} = {val}")
                    
                    if gps_tag_name == "GPSLatitude":
                        gps_coords["lat"] = val
                    elif gps_tag_name == "GPSLongitude":
                        gps_coords["lon"] = val
                    elif gps_tag_name == "GPSLatitudeRef":
                        gps_coords["lat_ref"] = val
                    elif gps_tag_name == "GPSLongitudeRef":
                        gps_coords["lon_ref"] = val
        
        # Verificar si tenemos todos los datos GPS necesarios
        if "lat" in gps_coords and "lon" in gps_coords and "lat_ref" in gps_coords and "lon_ref" in gps_coords:
            # Convertir coordenadas a grados decimales
            lat = _convert_to_degrees(gps_coords["lat"])
            lon = _convert_to_degrees(gps_coords["lon"])
            
            # Ajustar según referencia
            if gps_coords["lat_ref"] == 'S':
                lat = -lat
            if gps_coords["lon_ref"] == 'W':
                lon = -lon
            
            logger.info(f"✅ GPS extracted via Pillow _getexif(): ({lat:.6f}, {lon:.6f})")
            return lat, lon
        else:
            logger.warning(f"❌ GPS data incomplete via _getexif(). Found: {list(gps_coords.keys())}")
            return None, None
            
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None, None
    except Exception as e:
        logger.error(f"Error extracting GPS from {file_path}: {e}", exc_info=True)
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

    # BunnyCDN: usar transformaciones del CDN (Image Classes o parámetros) en lugar de ficheros redimensionados locales
    if provider == 'bunny':
        key_to_use = image_filename.lstrip('/')  # usamos siempre el nombre base que se subió
        current_app.logger.debug(f'☁️ Using BunnyCDN, base key={key_to_use}')

        # 1) Intentar mapear tamaños lógicos a Image Classes de BunnyCDN (recomendado)
        # Configura estas clases en Bunny:
        #  - thumbnail: 150x150 crop 1:1
        #  - medium:    tamaño para listados
        #  - large:     tamaño para detalle (opcional)
        size_classes = {
            'thumbnail': 'thumbnail',
            'large': 'large',
            'original': None,  # sin clase = original
        }
        bunny_class = size_classes.get(size, None)

        # Si el provider implementa url_for_resized, usarlo
        if hasattr(storage, 'url_for_resized'):
            try:
                if bunny_class:
                    # Usar Image Class de BunnyCDN
                    url = storage.url_for_resized(key_to_use, **{'class': bunny_class})
                else:
                    # Sin clase => URL base sin transformaciones
                    url = storage.url_for(key_to_use)
                current_app.logger.debug(f'✅ get_image_url (bunny): Returning URL={url}')
                return url
            except Exception as e:
                current_app.logger.warning(f'⚠️ get_image_url (bunny): Error with key {key_to_use}: {e}')
                # Fallback a url_for normal
                try:
                    url = storage.url_for(key_to_use)
                    current_app.logger.debug(f'✅ get_image_url (bunny): Fallback URL={url}')
                    return url
                except Exception as e2:
                    current_app.logger.error(f'❌ get_image_url (bunny): Both attempts failed: {e2}')
                    return None
        else:
            # Si no hay url_for_resized, usar url_for normal
            try:
                url = storage.url_for(key_to_use)
                current_app.logger.debug(f'✅ get_image_url (bunny,no-resize): URL={url}')
                return url
            except Exception as e:
                current_app.logger.error(f'❌ get_image_url (bunny,no-resize): Error: {e}')
                return None

    # Local storage: buscar fichero redimensionado en disco
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
    """Get translated inventory category and subcategory names from BD (with fallback)"""
    from flask_babel import gettext as _
    from flask import current_app
    from app.models import InventoryCategory
    
    try:
        # Intentar cargar desde BD
        main_cat = InventoryCategory.query.filter_by(
            code=category,
            parent_id=None,
            is_active=True
        ).first()
        
        if main_cat:
            main_name = main_cat.get_name()
            
            if subcategory:
                sub_cat = InventoryCategory.query.filter_by(
                    code=subcategory,
                    parent_id=main_cat.id,
                    is_active=True
                ).first()
                
                if sub_cat:
                    sub_name = sub_cat.get_name()
                    return f"{main_name} → {sub_name}"
                else:
                    # Subcategoría no encontrada en BD, usar fallback
                    return f"{main_name} → {_get_inventory_subcategory_name_fallback(subcategory)}"
            
            return main_name
        else:
            # Categoría no encontrada en BD, usar fallback
            return _get_inventory_category_name_fallback(category, subcategory)
    except Exception as e:
        # Si hay error accediendo a BD, usar fallback
        if current_app:
            current_app.logger.warning(f"Error loading category name from DB, using fallback: {e}")
        return _get_inventory_category_name_fallback(category, subcategory)

def _get_inventory_category_name_fallback(category, subcategory=None):
    """Fallback: obtener nombres hardcoded (para compatibilidad)"""
    from flask_babel import gettext as _
    
    # Mapeo de códigos antiguos a nuevos (para compatibilidad)
    category_map = {
        'palomas': 'coloms',
        'basura': 'contenidors',
        'perros': 'canis',
        'material_deteriorat': 'mobiliari_deteriorat',
        'mobiliari_urba': 'mobiliari_deteriorat',
    }
    
    # Normalizar código de categoría
    normalized_category = category_map.get(category, category)
    
    # Mapeo de subcategorías antiguas a nuevas
    subcategory_map = {
        'excremento': 'excrement',
        'nido': 'niu',
        'vertidos': 'abocaments',
    }
    
    normalized_subcategory = subcategory_map.get(subcategory, subcategory) if subcategory else None
    
    # Intentar obtener traducción usando el código normalizado
    main_name = _(normalized_category) if normalized_category else category
    
    if normalized_subcategory:
        sub_name = _(normalized_subcategory)
        return f"{main_name} → {sub_name}"
    
    return main_name

def get_inventory_subcategory_name(subcategory):
    """Get translated subcategory name only from BD (with fallback)"""
    from flask_babel import gettext as _
    from flask import current_app
    from app.models import InventoryCategory
    
    try:
        # Intentar cargar desde BD
        sub_cat = InventoryCategory.query.filter_by(
            code=subcategory,
            parent_id__isnot=None,  # Debe ser una subcategoría
            is_active=True
        ).first()
        
        if sub_cat:
            return sub_cat.get_name()
        else:
            # Subcategoría no encontrada en BD, usar fallback
            return _get_inventory_subcategory_name_fallback(subcategory)
    except Exception as e:
        # Si hay error accediendo a BD, usar fallback
        if current_app:
            current_app.logger.warning(f"Error loading subcategory name from DB, using fallback: {e}")
        return _get_inventory_subcategory_name_fallback(subcategory)

def _get_inventory_subcategory_name_fallback(subcategory):
    """Fallback: obtener nombre de subcategoría hardcoded (para compatibilidad)"""
    from flask_babel import gettext as _
    
    # Mapeo de subcategorías antiguas a nuevas
    subcategory_map = {
        'excremento': 'excrement',
        'nido': 'niu',
        'vertidos': 'abocaments',
        'escombreries_desbordades': 'deixadesa',
        'basura_desbordada': 'deixadesa',
    }
    
    normalized_subcategory = subcategory_map.get(subcategory, subcategory)
    return _(normalized_subcategory) if normalized_subcategory else subcategory

def get_inventory_emoji(category, subcategory=None):
    """
    Get emoji or icon string for inventory category/subcategory from BD.
    Returns the raw icon/emoji string from the database, or None if not found.
    
    Args:
        category: Main category code (e.g., 'coloms', 'contenidors')
        subcategory: Optional subcategory code (e.g., 'niu', 'excrement', 'ploma')
    
    Returns:
        str: Emoji or icon string (e.g., '🪺', '💩', 'fa-dove') or None
    """
    from flask import current_app
    from app.models import InventoryCategory
    
    try:
        if subcategory:
            # Buscar subcategoría específica
            main_cat = InventoryCategory.query.filter_by(
                code=category,
                parent_id=None,
                is_active=True
            ).first()
            
            if main_cat:
                sub_cat = InventoryCategory.query.filter_by(
                    code=subcategory,
                    parent_id=main_cat.id,
                    is_active=True
                ).first()
                
                if sub_cat and sub_cat.icon:
                    return sub_cat.icon
        else:
            # Buscar categoría principal
            main_cat = InventoryCategory.query.filter_by(
                code=category,
                parent_id=None,
                is_active=True
            ).first()
            
            if main_cat and main_cat.icon:
                return main_cat.icon
    except Exception as e:
        if current_app:
            current_app.logger.warning(f"Error loading emoji from DB: {e}")
    
    # Fallback: mapeo hardcoded de emojis
    emoji_map = {
        ('coloms', 'niu'): '🪺',
        ('coloms', 'excrement'): '💩',
        ('coloms', 'ploma'): '🪶',
        ('coloms', None): '🕊️',
        ('contenidors', 'abocaments'): '💧',
        ('contenidors', 'deixadesa'): '🧹',
        ('contenidors', None): '🗑️',
        ('canis', 'excrements'): '💩',
        ('canis', 'pixades'): '💧',
        ('canis', None): '🐕',
        # Compatibilidad con códigos antiguos
        ('palomas', 'nido'): '🪺',
        ('palomas', 'excremento'): '💩',
        ('palomas', 'plumas'): '🪶',
        ('basura', 'escombreries_desbordades'): '🗑️',
        ('basura', 'basura_desbordada'): '🗑️',
        ('basura', 'vertidos'): '💧',
    }
    
    # Normalizar códigos para compatibilidad
    category_map = {
        'palomas': 'coloms',
        'basura': 'contenidors',
        'perros': 'canis',
    }
    
    subcategory_map = {
        'excremento': 'excrement',
        'nido': 'niu',
        'plumas': 'ploma',
        'vertidos': 'abocaments',
    }
    
    normalized_category = category_map.get(category, category)
    normalized_subcategory = subcategory_map.get(subcategory, subcategory) if subcategory else None
    
    return emoji_map.get((normalized_category, normalized_subcategory), '📌')

def get_inventory_icon(category, subcategory=None):
    """
    Get Font Awesome icon class for inventory category/subcategory.
    Returns a tuple of (icon_class, color_class) for use in templates.
    Tries to get icon from BD first, falls back to hardcoded mapping.
    
    Args:
        category: Main category code (e.g., 'coloms', 'contenidors')
        subcategory: Optional subcategory code (e.g., 'niu', 'excrement', 'ploma')
    
    Returns:
        tuple: (icon_class, color_class) e.g., ('fa-dove', 'text-primary')
    """
    from flask import current_app
    from app.models import InventoryCategory
    
    try:
        # Intentar obtener icono desde BD
        if subcategory:
            # Buscar subcategoría específica
            main_cat = InventoryCategory.query.filter_by(
                code=category,
                parent_id=None,
                is_active=True
            ).first()
            
            if main_cat:
                sub_cat = InventoryCategory.query.filter_by(
                    code=subcategory,
                    parent_id=main_cat.id,
                    is_active=True
                ).first()
                
                if sub_cat and sub_cat.icon:
                    # Si el icono es una clase Font Awesome (empieza con 'fa-'), usarla
                    if sub_cat.icon.startswith('fa-'):
                        return (sub_cat.icon, 'text-secondary')
                    # Si es un emoji, usar fallback
        else:
            # Buscar categoría principal
            main_cat = InventoryCategory.query.filter_by(
                code=category,
                parent_id=None,
                is_active=True
            ).first()
            
            if main_cat and main_cat.icon:
                if main_cat.icon.startswith('fa-'):
                    return (main_cat.icon, 'text-secondary')
    except Exception as e:
        if current_app:
            current_app.logger.warning(f"Error loading icon from DB, using fallback: {e}")
    
    # Fallback: usar mapeo hardcoded (con compatibilidad para códigos antiguos)
    # Mapeo de códigos antiguos a nuevos
    category_map = {
        'palomas': 'coloms',
        'basura': 'contenidors',
        'perros': 'canis',
        'material_deteriorat': 'mobiliari_deteriorat',
        'mobiliari_urba': 'mobiliari_deteriorat',
    }
    
    subcategory_map = {
        'excremento': 'excrement',
        'nido': 'niu',
        'vertidos': 'abocaments',
    }
    
    normalized_category = category_map.get(category, category)
    normalized_subcategory = subcategory_map.get(subcategory, subcategory) if subcategory else None
    
    # Mapping: (category, subcategory) -> (icon_class, color_class)
    icon_mapping = {
        # Coloms (nuevo código)
        ('coloms', 'niu'): ('fa-home', 'text-primary'),
        ('coloms', 'excrement'): ('fa-biohazard', 'text-danger'),
        ('coloms', 'ploma'): ('fa-feather', 'text-info'),
        ('coloms', None): ('fa-dove', 'text-primary'),
        # Palomas (código antiguo - compatibilidad)
        ('palomas', 'nido'): ('fa-home', 'text-primary'),
        ('palomas', 'excremento'): ('fa-biohazard', 'text-danger'),
        ('palomas', 'plumas'): ('fa-feather', 'text-info'),  # Legacy - maps to 'ploma'
        ('palomas', None): ('fa-dove', 'text-primary'),
        
        # Contenidors (nuevo código)
        ('contenidors', 'abocaments'): ('fa-tint', 'text-danger'),
        ('contenidors', 'deixadesa'): ('fa-trash-alt', 'text-warning'),
        ('contenidors', None): ('fa-trash', 'text-secondary'),
        # Basura (código antiguo - compatibilidad)
        ('basura', 'vertidos'): ('fa-tint', 'text-danger'),
        ('basura', 'escombreries_desbordades'): ('fa-trash-alt', 'text-warning'),
        ('basura', None): ('fa-trash', 'text-secondary'),
        
        # Canis (nuevo código)
        ('canis', 'excrements'): ('fa-poop', 'text-danger'),
        ('canis', 'pixades'): ('fa-tint', 'text-warning'),
        ('canis', None): ('fa-dog', 'text-secondary'),
        # Perros (código antiguo - compatibilidad)
        ('perros', 'excrements'): ('fa-poop', 'text-danger'),
        ('perros', 'pixades'): ('fa-tint', 'text-warning'),
        ('perros', None): ('fa-dog', 'text-secondary'),
        
        # Mobiliari Deteriorat (nuevo código - mergeado)
        ('mobiliari_deteriorat', 'faroles'): ('fa-lightbulb', 'text-warning'),
        ('mobiliari_deteriorat', 'bancs'): ('fa-chair', 'text-info'),
        ('mobiliari_deteriorat', 'senyals'): ('fa-sign', 'text-warning'),
        ('mobiliari_deteriorat', 'paviment'): ('fa-road', 'text-danger'),
        ('mobiliari_deteriorat', 'papereres'): ('fa-trash', 'text-info'),
        ('mobiliari_deteriorat', 'parades'): ('fa-bus', 'text-primary'),
        ('mobiliari_deteriorat', None): ('fa-tools', 'text-secondary'),
        # Material Deteriorat / Mobiliari Urbà (códigos antiguos - compatibilidad)
        ('material_deteriorat', 'faroles'): ('fa-lightbulb', 'text-warning'),
        ('material_deteriorat', 'bancs'): ('fa-chair', 'text-info'),
        ('material_deteriorat', 'senyals'): ('fa-sign', 'text-warning'),
        ('material_deteriorat', 'paviment'): ('fa-road', 'text-danger'),
        ('material_deteriorat', None): ('fa-tools', 'text-secondary'),
        ('mobiliari_urba', 'papereres'): ('fa-trash', 'text-info'),
        ('mobiliari_urba', 'parades'): ('fa-bus', 'text-primary'),
        ('mobiliari_urba', 'bancs'): ('fa-chair', 'text-info'),
        ('mobiliari_urba', None): ('fa-city', 'text-secondary'),
        
        # Brutícia
        ('bruticia', 'terra'): ('fa-mountain', 'text-warning'),
        ('bruticia', 'fulles'): ('fa-leaf', 'text-success'),
        ('bruticia', 'grafit'): ('fa-spray-can', 'text-danger'),
        ('bruticia', None): ('fa-broom', 'text-secondary'),
        
        # Vandalisme (nuevo)
        ('vandalisme', 'pintades'): ('fa-spray-can', 'text-danger'),
        ('vandalisme', None): ('fa-spray-can', 'text-danger'),
        
        # Vegetació
        ('vegetacio', 'arbres'): ('fa-tree', 'text-success'),
        ('vegetacio', 'arbustos'): ('fa-seedling', 'text-success'),
        ('vegetacio', 'gespa'): ('fa-grass', 'text-success'),
        ('vegetacio', None): ('fa-tree', 'text-success'),
        
        # Infraestructura
        ('infraestructura', 'carreteres'): ('fa-road', 'text-danger'),
        ('infraestructura', 'voreres'): ('fa-walking', 'text-info'),
        ('infraestructura', 'enllumenat'): ('fa-lightbulb', 'text-warning'),
        ('infraestructura', None): ('fa-building', 'text-secondary'),
    }
    
    # Try to get icon for specific category+subcategory combination (normalizado primero)
    key = (normalized_category, normalized_subcategory)
    if key in icon_mapping:
        return icon_mapping[key]
    
    # Fallback: intentar con códigos originales
    key = (category, subcategory)
    if key in icon_mapping:
        return icon_mapping[key]
    
    # Fallback to category only (normalizado)
    key = (normalized_category, None)
    if key in icon_mapping:
        return icon_mapping[key]
    
    # Fallback to category only (original)
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
# Updated to use new category codes (URL and DB now use same codes in Catalan)
CATEGORY_URL_TO_DB = {
    'coloms': 'coloms',  # Updated from 'palomas'
    'contenidors': 'contenidors',  # Updated from 'basura'
    'canis': 'canis',  # Updated from 'perros'
    'mobiliari_deteriorat': 'mobiliari_deteriorat',  # Merged from 'material_deteriorat' and 'mobiliari_urba'
    'bruticia': 'bruticia',
    'vandalisme': 'vandalisme',  # New category
    'vegetacio': 'vegetacio',
    'infraestructura': 'infraestructura',
    # Legacy codes for backward compatibility
    'palomas': 'coloms',
    'basura': 'contenidors',
    'perros': 'canis',
    'material_deteriorat': 'mobiliari_deteriorat',
    'mobiliari_urba': 'mobiliari_deteriorat',
}

CATEGORY_DB_TO_URL = {
    'coloms': 'coloms',
    'contenidors': 'contenidors',
    'canis': 'canis',
    'mobiliari_deteriorat': 'mobiliari_deteriorat',
    'bruticia': 'bruticia',
    'vandalisme': 'vandalisme',
    'vegetacio': 'vegetacio',
    'infraestructura': 'infraestructura',
    # Legacy codes for backward compatibility
    'palomas': 'coloms',
    'basura': 'contenidors',
    'perros': 'canis',
    'material_deteriorat': 'mobiliari_deteriorat',
    'mobiliari_urba': 'mobiliari_deteriorat',
}

SUBCATEGORY_URL_TO_DB = {
    # Coloms (updated from Palomas)
    'niu': 'niu',  # Updated from 'nido'
    'excrement': 'excrement',  # Updated from 'excremento'
    'ploma': 'ploma',  # Updated from 'plumas'/'plomes'
    # Contenidors (updated from Basura)
    'abocaments': 'abocaments',  # Updated from 'vertidos'
    'deixadesa': 'deixadesa',  # New subcategory
    # Canis (updated from Perros)
    'excrements': 'excrements',
    'pixades': 'pixades',
    # Mobiliari Deteriorat (merged from Material Deteriorat and Mobiliari Urbà)
    'faroles': 'faroles',
    'bancs': 'bancs',
    'senyals': 'senyals',
    'paviment': 'paviment',
    'papereres': 'papereres',
    'parades': 'parades',
    # Brutícia
    'terra': 'terra',
    'fulles': 'fulles',
    'grafit': 'grafit',
    # Vandalisme (new category)
    'pintades': 'pintades',
    # Vegetació
    'arbres': 'arbres',
    'arbustos': 'arbustos',
    'gespa': 'gespa',
    # Infraestructura
    'carreteres': 'carreteres',
    'voreres': 'voreres',
    'enllumenat': 'enllumenat',
    # Legacy codes for backward compatibility
    'nido': 'niu',
    'excremento': 'excrement',
        'plumas': 'ploma',  # Legacy mapping
        'plomes': 'ploma',  # Legacy mapping
    'vertidos': 'abocaments',
    'escombreries_desbordades': 'deixadesa',
    'basura_desbordada': 'deixadesa',
}

SUBCATEGORY_DB_TO_URL = {
    # New codes
    'niu': 'niu',
    'excrement': 'excrement',
    'ploma': 'ploma',
    'abocaments': 'abocaments',
    'deixadesa': 'deixadesa',
    'excrements': 'excrements',
    'pixades': 'pixades',
    'faroles': 'faroles',
    'bancs': 'bancs',
    'senyals': 'senyals',
    'paviment': 'paviment',
    'papereres': 'papereres',
    'parades': 'parades',
    'terra': 'terra',
    'fulles': 'fulles',
    'grafit': 'grafit',
    'pintades': 'pintades',
    'arbres': 'arbres',
    'arbustos': 'arbustos',
    'gespa': 'gespa',
    'carreteres': 'carreteres',
    'voreres': 'voreres',
    'enllumenat': 'enllumenat',
    # Legacy codes for backward compatibility
    'nido': 'niu',
    'excremento': 'excrement',
        'plumas': 'ploma',  # Legacy mapping
        'plomes': 'ploma',  # Legacy mapping
    'vertidos': 'abocaments',
    'escombreries_desbordades': 'deixadesa',
    'basura_desbordada': 'deixadesa',
    'otro': 'altres',
}

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

