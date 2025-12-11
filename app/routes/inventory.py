from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_security import login_required, current_user
from flask_security.decorators import roles_required
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from app.models import InventoryItem, InventoryVote, InventoryResolved, District, Section, CityBoundary, InventoryItemStatus
from app.extensions import db
from app.forms import InventoryForm
from app.utils import (
    sanitize_html,
    allowed_file,
    optimize_image,
    extract_gps_from_image,
    calculate_distance_km,
    get_inventory_category_name,
    get_inventory_subcategory_name,
    normalize_category_from_url,
    normalize_subcategory_from_url,
    category_to_url,
    subcategory_to_url,
    get_image_path,
    get_image_url,
)
from app.core.decorators import section_responsible_required
# Config.UPLOAD_FOLDER removed - using current_app.config['UPLOAD_FOLDER'] instead

bp = Blueprint('inventory', __name__, url_prefix='/inventory')

@bp.route('')
def inventory_map():
    """Mapa principal del inventario"""
    # Get filter parameters from URL (en catalán)
    category_url = request.args.get('category')
    subcategory_url = request.args.get('subcategory')
    
    # Convertir de valores URL (catalán) a valores técnicos (BD)
    category = normalize_category_from_url(category_url)
    subcategory = normalize_subcategory_from_url(subcategory_url)
    
    # Build query - only show approved items (visible in map)
    query = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    )
    
    if category:
        query = query.filter(InventoryItem.category == category)
    if subcategory:
        query = query.filter(InventoryItem.subcategory == subcategory)
    
    items = query.order_by(InventoryItem.created_at.desc()).all()
    
    # Get statistics - only count approved items
    total_items = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).count()
    by_category = {}
    for item in InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).all():
        cat_key = f"{item.category}->{item.subcategory}"
        by_category[cat_key] = by_category.get(cat_key, 0) + 1
    
    # Ensure all items have importance_count set (fix for existing items)
    # This handles items created before the importance_count field was added
    items_without_count = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).all()
    fixed = False
    for item in items_without_count:
        if item.importance_count is None:
            item.importance_count = 0
            fixed = True
    if fixed:
        db.session.commit()
    
    # Group statistics by main category and subcategory
    by_main_category = {}
    by_subcategory = {}
    for item in InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).all():
        # Count by main category
        by_main_category[item.category] = by_main_category.get(item.category, 0) + 1
        # Count by subcategory (only if category is selected)
        if category and item.category == category:
            by_subcategory[item.subcategory] = by_subcategory.get(item.subcategory, 0) + 1
    
    return render_template('inventory/map.html',
                         items=items,
                         total_items=total_items,
                         by_category=by_category,
                         by_main_category=by_main_category,
                         by_subcategory=by_subcategory,
                         selected_category=category_url,  # Usar valor de URL para los templates
                         selected_subcategory=subcategory_url)  # Usar valor de URL para los templates

@bp.route('/report', methods=['GET', 'POST'])
@login_required
def report_item():
    """Formulario para reportar un item del inventario"""
    form = InventoryForm()
    # Set default category to 'palomas' if form is new (GET request)
    if request.method == 'GET' and not form.category.data:
        form.category.data = 'palomas'
    
    if form.validate_on_submit():
        try:
            # Handle image upload first (required)
            if not form.image.data:
                flash(_('La foto es obligatoria para reportar un item'), 'error')
                return render_template('inventory/report.html', form=form)
            
            file = form.image.data
            if not file or not allowed_file(file.filename):
                flash(_('Por favor, sube una imagen válida (JPG, PNG, GIF)'), 'error')
                return render_template('inventory/report.html', form=form)
            
            # Save image temporarily to extract GPS
            filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Try to extract GPS coordinates from image (PRIORITY 1)
            image_gps_lat, image_gps_lng = extract_gps_from_image(file_path)
            current_app.logger.info(f"📍 GPS extraído de imagen: lat={image_gps_lat}, lng={image_gps_lng}")
            
            latitude = image_gps_lat
            longitude = image_gps_lng
            location_source = 'image_gps'
            
            # If no GPS in image, use coordinates from form (from browser geolocation or manual) (PRIORITY 2)
            if latitude is None or longitude is None:
                current_app.logger.info("⚠️ No GPS en imagen, usando coordenadas del formulario")
                location_source = request.form.get('location_source') or 'form_coordinates'
                if form.latitude.data and form.longitude.data:
                    try:
                        latitude = float(form.latitude.data)
                        longitude = float(form.longitude.data)
                        current_app.logger.info(f"📍 Coordenadas del formulario: lat={latitude}, lng={longitude}")
                    except (ValueError, TypeError) as e:
                        current_app.logger.warning(f"❌ Error parseando coordenadas del formulario: {e}")
                        latitude = None
                        longitude = None
                else:
                    current_app.logger.warning("❌ No hay coordenadas en formulario ni GPS en imagen")
            
            # If still no coordinates, show error with helpful message
            if latitude is None or longitude is None:
                flash(_('No se pudo obtener la ubicación de la foto (no tiene coordenadas GPS). Por favor, selecciona la ubicación en el mapa o usa el botón "Usar la meva ubicació actual".'), 'error')
                # Clean up uploaded file
                if os.path.exists(file_path):
                    os.remove(file_path)
                # Pre-fill form with uploaded image info for retry
                form.category.data = form.category.data
                form.subcategory.data = form.subcategory.data
                form.description.data = form.description.data
                return render_template('inventory/report.html', form=form)

            # If both image GPS and chosen coords differ significantly, warn but keep user choice
            if image_gps_lat is not None and image_gps_lng is not None and latitude is not None and longitude is not None:
                try:
                    dist_km = calculate_distance_km(image_gps_lat, image_gps_lng, latitude, longitude)
                    if dist_km > 0.15:  # ~150 m
                        flash(
                            _('La ubicació seleccionada està a %(m)d m de la ubicació de la foto. Hem utilitzat la ubicació seleccionada.',
                              m=int(dist_km * 1000)),
                            'warning'
                        )
                        current_app.logger.warning(
                            f"Location differs from image GPS by {dist_km*1000:.1f} m "
                            f"(image_gps=({image_gps_lat},{image_gps_lng}), chosen=({latitude},{longitude}), source={location_source})"
                        )
                except Exception as e:
                    current_app.logger.warning(f"Error calculating distance image vs chosen coords: {e}")
            
            # Validate coordinates using CityBoundary (precise validation)
            if not CityBoundary.point_is_inside(latitude, longitude):
                current_app.logger.warning(
                    f'User {current_user.id} attempted to report item outside city boundary: '
                    f'lat={latitude}, lng={longitude}, source={location_source}'
                )
                flash(_('Les coordenades estan fora del límit de Tarragona. Si us plau, assegura\'t que la foto sigui dins de la ciutat o selecciona una ubicació dins del límit.'), 'error')
                # Clean up uploaded file
                if os.path.exists(file_path):
                    os.remove(file_path)
                return render_template('inventory/report.html', form=form)
            
            # Optimize original image (basic optimization, full resize will be done async)
            optimize_image(file_path)  # Basic optimization in place
            
            # Upload original file to storage (S3 or local)
            # This ensures the file is available even before async resize completes
            try:
                from app.storage import get_storage
                storage = get_storage()
                storage_provider = current_app.config.get('STORAGE_PROVIDER', 'local').lower()
                
                current_app.logger.info(f'📤 Uploading original file to storage (provider={storage_provider}): {filename}')
                storage.save(filename, file_path)
                current_app.logger.info(f'✅ Original file uploaded to storage: {filename}')
                
                # If using S3, delete local file after upload to save space
                if storage_provider == 's3':
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            current_app.logger.info(f'🗑️ Deleted local file after S3 upload: {file_path}')
                    except Exception as e:
                        current_app.logger.warning(f'⚠️ Could not delete local file {file_path}: {e}')
            except Exception as e:
                current_app.logger.error(f'❌ Error uploading original file to storage: {e}', exc_info=True)
                # Continue anyway - the file is still in local storage
            
            # Get address from form or geocode (optional)
            address = form.address.data if form.address.data else None
            
            # Create item with all data including GPS from image
            current_app.logger.info(
                f"💾 Guardando item con:\n"
                f"   - Ubicación final: lat={latitude}, lng={longitude}\n"
                f"   - GPS de imagen: lat={image_gps_lat}, lng={image_gps_lng}\n"
                f"   - Fuente: {location_source}"
            )
            
            item = InventoryItem(
                category=form.category.data,
                subcategory=form.subcategory.data,
                description=sanitize_html(form.description.data) if form.description.data else None,
                latitude=latitude,
                longitude=longitude,
                address=sanitize_html(address) if address else None,
                image_path=filename,  # Store original filename, will be updated by Celery task
                reporter_id=current_user.id,
                status='pending',
                # Store GPS from image for comparison (even if not used as final location)
                image_gps_latitude=image_gps_lat,
                image_gps_longitude=image_gps_lng,
                location_source=location_source
            )
            
            db.session.add(item)
            db.session.commit()
            
            # Enqueue image resizing task (async)
            try:
                resize_task = getattr(current_app, 'resize_image_task', None)
                if resize_task:
                    resize_task.delay(item.id, filename)
                    current_app.logger.info(f'📸 Image resizing task enqueued for item {item.id}: {filename}')
                else:
                    current_app.logger.warning('resize_image_task not available, skipping async resize')
            except Exception as e:
                current_app.logger.error(f'Error enqueueing image resize task: {e}', exc_info=True)
                # Continue anyway, image will be available in original size
            
            # Verify what was actually saved
            current_app.logger.info(
                f"✅ Item guardado (ID: {item.id}):\n"
                f"   - Ubicación final: lat={item.latitude}, lng={item.longitude}\n"
                f"   - GPS de imagen guardado: lat={item.image_gps_latitude}, lng={item.image_gps_longitude}\n"
                f"   - Fuente guardada: {item.location_source}"
            )
            
            current_app.logger.info(
                f'Inventory item reported: {item.category} at ({latitude}, {longitude}) '
                f'from {location_source} - Status: pending'
            )
            flash(_('¡Item reportado con éxito! Está pendiente de aprobación por un administrador.'), 'info')
            return redirect(url_for('inventory.inventory_map'))
        
        except ValueError:
            flash(_('Error: coordenadas inválidas'), 'error')
        except Exception as e:
            current_app.logger.error(f'Error reporting inventory item: {str(e)}', exc_info=True)
            flash(_('Error al reportar el item. Por favor, inténtalo de nuevo.'), 'error')
    
    return render_template('inventory/report.html', form=form)

@bp.route('/api/items')
def api_items():
    """API endpoint para obtener items del inventario (para el mapa)"""
    # Si se accede directamente desde el navegador, redirigir al mapa
    if request.headers.get('Accept', '').find('text/html') != -1:
        return redirect(url_for('inventory.inventory_map'))
    category_url = request.args.get('category')
    subcategory_url = request.args.get('subcategory')
    
    # Convertir de valores URL (catalán) a valores técnicos (BD)
    category = normalize_category_from_url(category_url)
    subcategory = normalize_subcategory_from_url(subcategory_url)
    
    # Only return approved items (visible in map)
    query = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    )
    
    if category:
        query = query.filter(InventoryItem.category == category)
    if subcategory:
        query = query.filter(InventoryItem.subcategory == subcategory)
    
    items = query.all()
    
    items_data = []
    user_id = current_user.id if current_user.is_authenticated else None
    
    for item in items:
        has_voted = item.has_user_voted(user_id) if user_id else False
        # Ensure importance_count is never None
        importance_count = item.importance_count if item.importance_count is not None else 0
        # Check if user has reported "ya no está"
        has_resolved = item.has_user_resolved(user_id) if user_id else False
        resolved_count = item.resolved_count if item.resolved_count is not None else 0
        
        items_data.append({
            'id': item.id,
            'category': item.category,
            'subcategory': item.subcategory,
            'full_category': get_inventory_category_name(item.category, item.subcategory),
            'description': item.description,
            'latitude': item.latitude,
            'longitude': item.longitude,
            'address': item.address,
            'image_path': item.image_path,
            'image_url': get_image_url(item.image_path, 'medium'),
            'image_url_thumbnail': get_image_url(item.image_path, 'thumbnail'),
            'importance_count': importance_count,
            'has_voted': has_voted,
            'resolved_count': resolved_count,
            'has_resolved': has_resolved,
            'created_at': item.created_at.isoformat() if item.created_at else None
        })
    
    return jsonify(items_data)

@bp.route('/api/sections')
def api_sections():
    """API endpoint para obtener todas las secciones con sus polígonos"""
    # Si se accede directamente desde el navegador, redirigir al mapa
    if request.headers.get('Accept', '').find('text/html') != -1:
        return redirect(url_for('inventory.inventory_map'))
    
    try:
        from shapely import wkt
        import json
        
        sections = Section.query.join(District).order_by(Section.district_code, Section.code).all()
        
        result = []
        for section in sections:
            if section.polygon:
                try:
                    # Parsear WKT a geometría Shapely
                    geom = wkt.loads(section.polygon)
                    
                    # No aplicar buffer - usar geometría original para evitar solapamientos
                    # Convertir a GeoJSON directamente
                    geojson = json.loads(json.dumps(geom.__geo_interface__))
                    
                    result.append({
                        'id': section.id,
                        'code': section.code,
                        'district_code': section.district_code,
                        'district_name': section.district.name,
                        'name': section.name or f"Secció {section.code}",
                        'full_code': section.full_code,
                        'geometry': geojson
                    })
                except Exception as e:
                    current_app.logger.warning(f"Error parsing polygon for section {section.id}: {e}")
                    continue
        
        return jsonify(result)
    except ImportError:
        current_app.logger.error("Shapely not available for WKT parsing")
        return jsonify({'error': 'WKT parsing not available'}), 500
    except Exception as e:
        current_app.logger.error(f"Error in api_sections: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/boundary')
def api_boundary():
    """API endpoint para obtener el boundary de la ciudad"""
    # Si se accede directamente desde el navegador, redirigir al mapa
    if request.headers.get('Accept', '').find('text/html') != -1:
        return redirect(url_for('inventory.inventory_map'))
    
    try:
        from shapely import wkt
        import json
        
        boundary = CityBoundary.query.first()
        
        if not boundary or not boundary.polygon:
            return jsonify({'error': 'City boundary not found'}), 404
        
        try:
            from sqlalchemy import func
            from app.extensions import db
            
            # Parsear WKT a geometría Shapely
            geom = wkt.loads(boundary.polygon)
            
            # Convertir a GeoJSON
            geojson = json.loads(json.dumps(geom.__geo_interface__))
            
            # Calcular bounding box usando PostGIS
            try:
                boundary_geom = func.ST_GeomFromText(boundary.polygon, 4326)
                bbox_result = db.session.query(
                    func.ST_XMin(func.ST_Envelope(boundary_geom)).label('min_lng'),
                    func.ST_YMin(func.ST_Envelope(boundary_geom)).label('min_lat'),
                    func.ST_XMax(func.ST_Envelope(boundary_geom)).label('max_lng'),
                    func.ST_YMax(func.ST_Envelope(boundary_geom)).label('max_lat')
                ).first()
                
                if bbox_result:
                    # Añadir un margen del 20% al bounding box para permitir algo de movimiento
                    lng_range = bbox_result.max_lng - bbox_result.min_lng
                    lat_range = bbox_result.max_lat - bbox_result.min_lat
                    margin_lng = lng_range * 0.2
                    margin_lat = lat_range * 0.2
                    
                    bounds = {
                        'southwest': [bbox_result.min_lat - margin_lat, bbox_result.min_lng - margin_lng],
                        'northeast': [bbox_result.max_lat + margin_lat, bbox_result.max_lng + margin_lng]
                    }
                else:
                    bounds = None
            except Exception as e:
                current_app.logger.warning(f"Error calculating bounds with PostGIS: {e}")
                # Fallback: usar Shapely para calcular bounds
                try:
                    bounds_obj = geom.bounds  # (minx, miny, maxx, maxy)
                    lng_range = bounds_obj[2] - bounds_obj[0]
                    lat_range = bounds_obj[3] - bounds_obj[1]
                    margin_lng = lng_range * 0.2
                    margin_lat = lat_range * 0.2
                    
                    bounds = {
                        'southwest': [bounds_obj[1] - margin_lat, bounds_obj[0] - margin_lng],
                        'northeast': [bounds_obj[3] + margin_lat, bounds_obj[2] + margin_lng]
                    }
                except Exception as e2:
                    current_app.logger.warning(f"Error calculating bounds with Shapely: {e2}")
                    bounds = None
            
            return jsonify({
                'id': boundary.id,
                'name': boundary.name,
                'calculated_at': boundary.calculated_at.isoformat() if boundary.calculated_at else None,
                'geometry': geojson,
                'bounds': bounds
            })
        except Exception as e:
            current_app.logger.error(f"Error parsing boundary polygon: {e}")
            return jsonify({'error': 'Error parsing boundary geometry'}), 500
        
    except ImportError:
        current_app.logger.error("Shapely not available for WKT parsing")
        return jsonify({'error': 'WKT parsing not available'}), 500
    except Exception as e:
        current_app.logger.error(f"Error in api_boundary: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:item_id>')
def item_detail(item_id):
    """Página de detalle de un item del inventario"""
    item = InventoryItem.query.get_or_404(item_id)
    
    # Check if user can view this item
    # Public can only see approved items
    if item.status != InventoryItemStatus.APPROVED.value:
        if not current_user.is_authenticated:
            from flask import abort
            abort(404)
        # Check if user is reporter, admin, or section responsible
        is_reporter = item.reporter_id == current_user.id
        is_admin = current_user.has_role('admin')
        is_section_responsible = False
        if item.section and current_user.has_role('section_responsible'):
            # Check if user is responsible for this section
            from app.models import SectionResponsible
            section_responsible = SectionResponsible.query.filter_by(
                user_id=current_user.id,
                section_id=item.section_id
            ).first()
            is_section_responsible = section_responsible is not None
        
        if not (is_reporter or is_admin or is_section_responsible):
            from flask import abort
            abort(404)
    
    # Check if user has voted/resolved
    has_voted = False
    has_resolved = False
    if current_user.is_authenticated:
        has_voted = InventoryVote.query.filter_by(
            item_id=item_id,
            user_id=current_user.id
        ).first() is not None
        has_resolved = InventoryResolved.query.filter_by(
            item_id=item_id,
            user_id=current_user.id
        ).first() is not None
    
    return render_template('inventory/detail.html',
                         item=item,
                         has_voted=has_voted,
                         has_resolved=has_resolved,
                         get_inventory_category_name=get_inventory_category_name,
                         get_inventory_subcategory_name=get_inventory_subcategory_name,
                         get_image_path=get_image_path)

@bp.route('/<int:item_id>/vote', methods=['POST'])
@login_required
def vote_item(item_id):
    """Votar/incrementar importancia de un item"""
    from app.extensions import csrf
    
    # CSRF is automatically validated by Flask-WTF for POST requests
    # If validation fails, it will raise an exception handled by Flask
    
    item = InventoryItem.query.get_or_404(item_id)
    
    # Check if user has already voted
    if item.has_user_voted(current_user.id):
        return jsonify({'error': _('Ya has votado este item')}), 400
    
    # Create vote
    vote = InventoryVote(item_id=item.id, user_id=current_user.id)
    db.session.add(vote)
    
    # Increment importance count (handle None case for existing items)
    if item.importance_count is None:
        item.importance_count = 0
    item.importance_count += 1
    db.session.commit()
    
    current_app.logger.info(f'User {current_user.id} voted for inventory item {item.id}')
    
    return jsonify({
        'success': True,
        'importance_count': item.importance_count,
        'resolved_count': item.resolved_count if item.resolved_count is not None else 0,
        'has_resolved': item.has_user_resolved(current_user.id),
        'message': _('Voto registrado correctamente')
    })

@bp.route('/<int:item_id>/resolve', methods=['POST'])
@login_required
def resolve_item(item_id):
    """Reportar que un item "ya no está" (resuelto)"""
    from app.extensions import csrf
    from app.models import InventoryResolved
    
    item = InventoryItem.query.get_or_404(item_id)
    
    # Check if user has already reported "ya no está"
    if item.has_user_resolved(current_user.id):
        return jsonify({'error': _('Ya has reportado que este item ya no está')}), 400
    
    # Don't allow resolving if item is already resolved
    if item.is_resolved():
        return jsonify({'error': _('Este item ya está marcado como resuelto')}), 400
    
    # Create resolved report
    resolved = InventoryResolved(item_id=item.id, user_id=current_user.id)
    db.session.add(resolved)
    
    # Increment resolved count
    if item.resolved_count is None:
        item.resolved_count = 0
    item.resolved_count += 1
    
    # Use the method that handles all the logic
    success, auto_resolved, message = item.add_resolved_report(current_user.id)
    
    if not success:
        return jsonify({'error': message}), 400
    
    db.session.commit()
    
    current_app.logger.info(f'User {current_user.id} reported item {item.id} as resolved (count: {item.resolved_count})')
    
    return jsonify({
        'success': True,
        'resolved_count': item.resolved_count,
        'importance_count': item.importance_count if item.importance_count is not None else 0,
        'has_voted': False,  # Now false since we removed it
        'status': item.status,
        'auto_resolved': auto_resolved,
        'message': message
    })

@bp.route('/admin/pending-map')
@login_required
@roles_required('admin')
def admin_pending_map():
    """Mapa de items pendientes para administradores"""
    items = InventoryItem.query.filter(InventoryItem.status == InventoryItemStatus.PENDING.value).order_by(InventoryItem.created_at.desc()).all()
    
    return render_template('inventory/admin_pending_map.html', items=items)

@bp.route('/admin/api/pending-items')
@login_required
@roles_required('admin')
def api_pending_items():
    """API endpoint para obtener items pendientes (para el mapa de admin)"""
    items = InventoryItem.query.filter(InventoryItem.status == InventoryItemStatus.PENDING.value).all()
    
    items_data = []
    for item in items:
        items_data.append({
            'id': item.id,
            'category': item.category,
            'subcategory': item.subcategory,
            'full_category': get_inventory_category_name(item.category, item.subcategory),
            'description': item.description,
            'latitude': item.latitude,
            'longitude': item.longitude,
            'address': item.address,
            'image_path': item.image_path,
            'reporter': item.reporter.username if item.reporter else None,
            'created_at': item.created_at.isoformat() if item.created_at else None
        })
    
    return jsonify(items_data)

@bp.route('/admin')
@login_required
@roles_required('admin')
def admin_inventory():
    """Panel de administración del inventario"""
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query
    query = InventoryItem.query
    if status_filter != 'all':
        query = query.filter(InventoryItem.status == status_filter)
    
    # Paginate results
    pagination = query.order_by(InventoryItem.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    items = pagination.items
    
    # Statistics
    total_items = InventoryItem.query.count()
    pending_items = InventoryItem.query.filter(InventoryItem.status == InventoryItemStatus.PENDING.value).count()
    approved_items = InventoryItem.query.filter(InventoryItem.status == InventoryItemStatus.APPROVED.value).count()
    resolved_items = InventoryItem.query.filter(InventoryItem.status == InventoryItemStatus.RESOLVED.value).count()
    rejected_items = InventoryItem.query.filter(InventoryItem.status == InventoryItemStatus.REJECTED.value).count()
    
    by_category = {}
    for item in InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).all():
        cat_key = f"{item.category}->{item.subcategory}"
        by_category[cat_key] = by_category.get(cat_key, 0) + 1
    
    return render_template('inventory/admin.html',
                         items=items,
                         pagination=pagination,
                         total_items=total_items,
                         pending_items=pending_items,
                         approved_items=approved_items,
                         resolved_items=resolved_items,
                         rejected_items=rejected_items,
                         by_category=by_category,
                         status_filter=status_filter,
                         page=page,
                         per_page=per_page)

@bp.route('/admin/<int:id>/resolve', methods=['POST'])
@login_required
@roles_required('admin')
def admin_resolve_item(id):
    """Marcar item como resuelto (admin)"""
    item = InventoryItem.query.get_or_404(id)
    success, message = item.resolve(resolved_by=current_user)
    if success:
        db.session.commit()
    else:
        flash(message, 'warning')
    
    flash(_('Item marcado como resuelto'), 'success')
    # Redirect back to the same page and filter (from form data or args)
    page = request.form.get('page', request.args.get('page', 1, type=int), type=int)
    status_filter = request.form.get('status', request.args.get('status', 'all'))
    per_page = request.form.get('per_page', request.args.get('per_page', 20, type=int), type=int)
    return redirect(url_for('inventory.admin_inventory', status=status_filter, page=page, per_page=per_page))


@bp.route('/admin/<int:id>/delete', methods=['POST'])
@login_required
@roles_required('admin')
def delete_item(id):
    """Eliminar item del inventario"""
    item = InventoryItem.query.get_or_404(id)
    
    # Delete associated image if exists
    if item.image_path:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], item.image_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(item)
    db.session.commit()
    
    flash(_('Item eliminado'), 'success')
    # Redirect back to the same page and filter (from form data or args)
    page = request.form.get('page', request.args.get('page', 1, type=int), type=int)
    status_filter = request.form.get('status', request.args.get('status', 'all'))
    per_page = request.form.get('per_page', request.args.get('per_page', 20, type=int), type=int)
    return redirect(url_for('inventory.admin_inventory', status=status_filter, page=page, per_page=per_page))


# ========== Rutas para Responsables de Sección ==========

@bp.route('/section-responsible')
@login_required
@section_responsible_required
def section_responsible_dashboard():
    """Dashboard para responsables de sección"""
    # Obtener secciones que gestiona el usuario
    managed_sections = current_user.get_managed_sections()
    section_ids = [s.id for s in managed_sections]
    
    if not section_ids:
        flash(_('No tienes secciones asignadas'), 'warning')
        return render_template('inventory/section_responsible.html',
                             items=[],
                             pagination=None,
                             managed_sections=[],
                             stats={'total': 0, 'pending': 0, 'approved': 0, 'resolved': 0},
                             status_filter='all')
    
    # Filtrar items solo de sus secciones
    query = InventoryItem.query.filter(InventoryItem.section_id.in_(section_ids))
    
    # Filtros
    status_filter = request.args.get('status', 'all')
    if status_filter != 'all':
        query = query.filter(InventoryItem.status == status_filter)
    
    # Paginación
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    pagination = query.order_by(InventoryItem.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Estadísticas
    stats = {
        'total': query.count(),
        'pending': query.filter(InventoryItem.status == InventoryItemStatus.PENDING.value).count(),
        'approved': query.filter(InventoryItem.status == InventoryItemStatus.APPROVED.value).count(),
        'resolved': query.filter(InventoryItem.status == InventoryItemStatus.RESOLVED.value).count(),
    }
    
    return render_template('inventory/section_responsible.html',
                         items=pagination.items,
                         pagination=pagination,
                         managed_sections=managed_sections,
                         stats=stats,
                         status_filter=status_filter)

@bp.route('/section-responsible/<int:id>/approve', methods=['POST'])
@login_required
@section_responsible_required
def section_responsible_approve(id):
    """Aprobar item (solo si es de una sección gestionada)"""
    item = InventoryItem.query.get_or_404(id)
    
    # Verificar que el item pertenece a una sección gestionada
    if not current_user.is_section_responsible(item.section_id):
        flash(_('No tienes permisos para gestionar este item'), 'error')
        return redirect(url_for('inventory.section_responsible_dashboard'))
    
    success, message = item.approve(approved_by=current_user)
    
    if not success:
        flash(message, 'warning')
    else:
        db.session.commit()
        flash(message, 'success')
    
    return redirect(url_for('inventory.section_responsible_dashboard'))

@bp.route('/section-responsible/<int:id>/resolve', methods=['POST'])
@login_required
@section_responsible_required
def section_responsible_resolve(id):
    """Marcar item como resuelto"""
    item = InventoryItem.query.get_or_404(id)
    
    if not current_user.is_section_responsible(item.section_id):
        flash(_('No tienes permisos para gestionar este item'), 'error')
        return redirect(url_for('inventory.section_responsible_dashboard'))
    
    success, message = item.resolve(resolved_by=current_user)
    
    if not success:
        flash(message, 'warning')
    else:
        db.session.commit()
        flash(message, 'success')
    
    return redirect(url_for('inventory.section_responsible_dashboard'))
