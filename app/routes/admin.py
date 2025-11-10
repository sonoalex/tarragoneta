from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_security import login_required, current_user
from flask_security.decorators import roles_required
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from app.models import Initiative, User, Participation, user_initiatives, InventoryItem
from app.extensions import db
from app.forms import InitiativeForm
from app.utils import sanitize_html, allowed_file, optimize_image
# Config.UPLOAD_FOLDER removed - using current_app.config['UPLOAD_FOLDER'] instead
from flask_babel import gettext as _

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@login_required
@roles_required('admin')
def admin_dashboard():
    current_app.logger.info(f'Admin dashboard accessed by {current_user.email}')
    initiatives = Initiative.query.order_by(Initiative.created_at.desc()).all()
    users_count = User.query.count()
    participations_count = db.session.query(db.func.count(user_initiatives.c.user_id)).scalar() or 0
    participations_count += Participation.query.count()
    
    # Get recent participations
    recent_participations = Participation.query.order_by(Participation.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         initiatives=initiatives,
                         users_count=users_count,
                         participations_count=participations_count,
                         recent_participations=recent_participations)

@bp.route('/initiative/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def new_initiative():
    form = InitiativeForm()
    
    if form.validate_on_submit():
        # Generate slug from title
        from app.utils import generate_slug
        base_slug = generate_slug(form.title.data)
        slug = base_slug
        counter = 1
        # Ensure slug is unique
        while Initiative.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        initiative = Initiative(
            title=sanitize_html(form.title.data),
            slug=slug,
            description=sanitize_html(form.description.data),
            location=sanitize_html(form.location.data),
            category=form.category.data,
            date=form.date.data,
            time=sanitize_html(form.time.data) if form.time.data else None,
            creator_id=current_user.id
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
                    initiative.image_path = filename
        
        db.session.add(initiative)
        db.session.commit()
        
        flash('Iniciativa creada con éxito', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('admin/new_initiative.html', form=form)

@bp.route('/initiative/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def edit_initiative(id):
    initiative = Initiative.query.get_or_404(id)
    form = InitiativeForm(obj=initiative)
    
    if form.validate_on_submit():
        # Update slug if title changed
        if initiative.title != form.title.data:
            from app.utils import generate_slug
            base_slug = generate_slug(form.title.data)
            slug = base_slug
            counter = 1
            # Ensure slug is unique
            while Initiative.query.filter(Initiative.slug == slug, Initiative.id != initiative.id).first():
                slug = f"{base_slug}-{counter}"
                counter += 1
            initiative.slug = slug
        
        initiative.title = sanitize_html(form.title.data)
        initiative.description = sanitize_html(form.description.data)
        initiative.location = sanitize_html(form.location.data)
        initiative.category = form.category.data
        initiative.date = form.date.data
        initiative.time = sanitize_html(form.time.data) if form.time.data else None
        initiative.updated_at = datetime.utcnow()
        
        # Handle image upload
        if form.image.data:
            file = form.image.data
            if file and allowed_file(file.filename):
                # Delete old image if exists
                if initiative.image_path:
                    old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], initiative.image_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                if optimize_image(file_path):
                    initiative.image_path = filename
        
        db.session.commit()
        flash('Iniciativa actualizada con éxito', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('admin/edit_initiative.html', form=form, initiative=initiative)

@bp.route('/initiative/<int:id>/delete', methods=['POST'])
@login_required
@roles_required('admin')
def delete_initiative(id):
    initiative = Initiative.query.get_or_404(id)
    
    # Delete associated image if exists
    if initiative.image_path:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], initiative.image_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(initiative)
    db.session.commit()
    
    flash('Iniciativa eliminada con éxito', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@bp.route('/users')
@login_required
@roles_required('admin')
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@bp.route('/participations')
@login_required
@roles_required('admin')
def admin_participations():
    participations = Participation.query.order_by(Participation.created_at.desc()).all()
    return render_template('admin/participations.html', participations=participations)

@bp.route('/inventory/<int:id>/approve', methods=['POST'])
@login_required
@roles_required('admin')
def approve_item(id):
    """Aprobar un item pendiente del inventario"""
    item = InventoryItem.query.get_or_404(id)
    
    if item.status != 'pending':
        flash(_('Este item no está pendiente de aprobación'), 'warning')
        return redirect(url_for('inventory.admin_inventory'))
    
    item.status = 'approved'
    item.updated_at = datetime.utcnow()
    db.session.commit()
    
    current_app.logger.info(f'Admin {current_user.id} approved inventory item {item.id}')
    flash(_('Item aprobado correctamente'), 'success')
    # Redirect back to pending page with pagination (from form data or args)
    page = request.form.get('page', request.args.get('page', 1, type=int), type=int)
    per_page = request.form.get('per_page', request.args.get('per_page', 20, type=int), type=int)
    return redirect(url_for('inventory.admin_inventory', status='pending', page=page, per_page=per_page))

@bp.route('/inventory/<int:id>/reject', methods=['POST'])
@login_required
@roles_required('admin')
def reject_item(id):
    """Rechazar un item pendiente del inventario"""
    item = InventoryItem.query.get_or_404(id)
    
    if item.status != 'pending':
        flash(_('Este item no está pendiente de aprobación'), 'warning')
        return redirect(url_for('inventory.admin_inventory'))
    
    item.status = 'rejected'
    item.updated_at = datetime.utcnow()
    db.session.commit()
    
    current_app.logger.info(f'Admin {current_user.id} rejected inventory item {item.id}')
    flash(_('Item rechazado'), 'info')
    # Redirect back to pending page with pagination (from form data or args)
    page = request.form.get('page', request.args.get('page', 1, type=int), type=int)
    per_page = request.form.get('per_page', request.args.get('per_page', 20, type=int), type=int)
    return redirect(url_for('inventory.admin_inventory', status='pending', page=page, per_page=per_page))

