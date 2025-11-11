from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_security import login_required, current_user
from flask_security.decorators import roles_required
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from app.models import InventoryItem, InventoryVote
from app.extensions import db
from app.forms import InventoryForm
from app.utils import sanitize_html, allowed_file, optimize_image, get_inventory_category_name
# Config.UPLOAD_FOLDER removed - using current_app.config['UPLOAD_FOLDER'] instead

bp = Blueprint('inventory', __name__, url_prefix='/inventory')

@bp.route('')
def inventory_map():
    """Mapa principal del inventario"""
    # Get filter parameters
    category = request.args.get('category')
    subcategory = request.args.get('subcategory')
    
    # Build query - only show approved or active items
    query = InventoryItem.query.filter(
        InventoryItem.status.in_(['approved', 'active'])
    )
    
    if category:
        query = query.filter(InventoryItem.category == category)
    if subcategory:
        query = query.filter(InventoryItem.subcategory == subcategory)
    
    items = query.order_by(InventoryItem.created_at.desc()).all()
    
    # Get statistics - only count approved/active items
    total_items = InventoryItem.query.filter(
        InventoryItem.status.in_(['approved', 'active'])
    ).count()
    by_category = {}
    for item in InventoryItem.query.filter(
        InventoryItem.status.in_(['approved', 'active'])
    ).all():
        cat_key = f"{item.category}->{item.subcategory}"
        by_category[cat_key] = by_category.get(cat_key, 0) + 1
    
    # Ensure all items have importance_count set (fix for existing items)
    # This handles items created before the importance_count field was added
    items_without_count = InventoryItem.query.filter(
        InventoryItem.status.in_(['approved', 'active'])
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
        InventoryItem.status.in_(['approved', 'active'])
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
                         selected_category=category,
                         selected_subcategory=subcategory)

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
            latitude = float(form.latitude.data)
            longitude = float(form.longitude.data)
            
            # Validate coordinates (Tarragona area approximately)
            if not (40.5 <= latitude <= 41.5 and 0.5 <= longitude <= 2.0):
                flash(_('Las coordenadas están fuera del área de Tarragona'), 'error')
                return render_template('inventory/report.html', form=form)
            
            item = InventoryItem(
                category=form.category.data,
                subcategory=form.subcategory.data,
                description=sanitize_html(form.description.data) if form.description.data else None,
                latitude=latitude,
                longitude=longitude,
                address=sanitize_html(form.address.data) if form.address.data else None,
                reporter_id=current_user.id,  # Always authenticated due to @login_required
                status='pending'  # New items require admin approval
            )
            
            # Handle image upload
            if form.image.data:
                file = form.image.data
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    
                    # Optimize image
                    if optimize_image(file_path):
                        item.image_path = filename
            
            db.session.add(item)
            db.session.commit()
            
            current_app.logger.info(f'Inventory item reported: {item.category} at ({latitude}, {longitude}) - Status: pending')
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
    category = request.args.get('category')
    subcategory = request.args.get('subcategory')
    
    # Only return approved or active items
    query = InventoryItem.query.filter(
        InventoryItem.status.in_(['approved', 'active'])
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
            'importance_count': importance_count,
            'has_voted': has_voted,
            'created_at': item.created_at.isoformat() if item.created_at else None
        })
    
    return jsonify(items_data)

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
        'message': _('Voto registrado correctamente')
    })

@bp.route('/admin/pending-map')
@login_required
@roles_required('admin')
def admin_pending_map():
    """Mapa de items pendientes para administradores"""
    items = InventoryItem.query.filter(InventoryItem.status == 'pending').order_by(InventoryItem.created_at.desc()).all()
    
    return render_template('inventory/admin_pending_map.html', items=items)

@bp.route('/admin/api/pending-items')
@login_required
@roles_required('admin')
def api_pending_items():
    """API endpoint para obtener items pendientes (para el mapa de admin)"""
    items = InventoryItem.query.filter(InventoryItem.status == 'pending').all()
    
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
    pending_items = InventoryItem.query.filter(InventoryItem.status == 'pending').count()
    approved_items = InventoryItem.query.filter(InventoryItem.status == 'approved').count()
    active_items = InventoryItem.query.filter(InventoryItem.status == 'active').count()
    resolved_items = InventoryItem.query.filter(InventoryItem.status == 'resolved').count()
    rejected_items = InventoryItem.query.filter(InventoryItem.status == 'rejected').count()
    
    by_category = {}
    for item in InventoryItem.query.filter(
        InventoryItem.status.in_(['approved', 'active'])
    ).all():
        cat_key = f"{item.category}->{item.subcategory}"
        by_category[cat_key] = by_category.get(cat_key, 0) + 1
    
    return render_template('inventory/admin.html',
                         items=items,
                         pagination=pagination,
                         total_items=total_items,
                         pending_items=pending_items,
                         approved_items=approved_items,
                         active_items=active_items,
                         resolved_items=resolved_items,
                         rejected_items=rejected_items,
                         by_category=by_category,
                         status_filter=status_filter,
                         page=page,
                         per_page=per_page)

@bp.route('/admin/<int:id>/resolve', methods=['POST'])
@login_required
@roles_required('admin')
def resolve_item(id):
    """Marcar item como resuelto"""
    item = InventoryItem.query.get_or_404(id)
    item.status = 'resolved'
    item.updated_at = datetime.now()
    db.session.commit()
    
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

