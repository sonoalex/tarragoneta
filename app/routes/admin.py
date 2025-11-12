from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_security import login_required, current_user
from flask_security.decorators import roles_required
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from app.models import Initiative, User, Participation, user_initiatives, InventoryItem, Donation
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
    
    # Pagination for initiatives
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Initiative.query.order_by(Initiative.created_at.desc())
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    initiatives = pagination.items
    
    users_count = User.query.count()
    participations_count = db.session.query(db.func.count(user_initiatives.c.user_id)).scalar() or 0
    participations_count += Participation.query.count()
    pending_initiatives_count = Initiative.query.filter(Initiative.status == 'pending').count()
    
    # Donation statistics
    total_donations = Donation.query.filter(Donation.status == 'completed').count()
    total_donated = db.session.query(db.func.sum(Donation.amount)).filter(Donation.status == 'completed').scalar() or 0
    total_donated_euros = total_donated / 100 if total_donated else 0
    recent_donations = Donation.query.filter(Donation.status == 'completed').order_by(Donation.completed_at.desc()).limit(5).all()
    
    # Get recent participations
    recent_participations = Participation.query.order_by(Participation.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         initiatives=initiatives,
                         pagination=pagination,
                         users_count=users_count,
                         participations_count=participations_count,
                         recent_participations=recent_participations,
                         pending_initiatives_count=pending_initiatives_count,
                         total_donations=total_donations,
                         total_donated_euros=total_donated_euros,
                         recent_donations=recent_donations)

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
        
        # Get status from form or default to approved for admin
        status = form.status.data if form.status.data else 'approved'
        
        initiative = Initiative(
            title=sanitize_html(form.title.data),
            slug=slug,
            description=sanitize_html(form.description.data),
            location=sanitize_html(form.location.data),
            category=form.category.data,
            date=form.date.data,
            time=sanitize_html(form.time.data) if form.time.data else None,
            creator_id=current_user.id,
            status=status
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
    # Set current status
    form.status.data = initiative.status
    
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
        # Update status if provided (only for admin editing)
        if form.status.data:
            initiative.status = form.status.data
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
    """Lista de usuarios - DataTables maneja la paginación y búsqueda"""
    from app.models import Role
    
    # Obtener todos los usuarios (DataTables manejará la paginación en el cliente)
    users = User.query.order_by(User.created_at.desc()).all()
    
    # Estadísticas
    total_users = User.query.count()
    active_users = User.query.filter(User.active == True).count()
    inactive_users = User.query.filter(User.active == False).count()
    unconfirmed_users = User.query.filter(User.confirmed_at == None).count()
    
    # Roles disponibles
    all_roles = Role.query.all()
    
    return render_template('admin/users.html',
                         users=users,
                         total_users=total_users,
                         active_users=active_users,
                         inactive_users=inactive_users,
                         unconfirmed_users=unconfirmed_users,
                         all_roles=all_roles)

@bp.route('/users/<int:id>/toggle-active', methods=['POST'])
@login_required
@roles_required('admin')
def toggle_user_active(id):
    """Activar o desactivar un usuario"""
    user = User.query.get_or_404(id)
    
    # No permitir desactivarse a sí mismo
    if user.id == current_user.id:
        flash(_('No puedes desactivar tu propia cuenta'), 'error')
        return redirect(url_for('admin.admin_users'))
    
    user.active = not user.active
    db.session.commit()
    
    status = _('activado') if user.active else _('desactivado')
    current_app.logger.info(f'Admin {current_user.id} {"activated" if user.active else "deactivated"} user {user.id}')
    flash(_('Usuario {} correctamente').format(status), 'success')
    return redirect(url_for('admin.admin_users'))

@bp.route('/users/<int:id>/confirm', methods=['POST'])
@login_required
@roles_required('admin')
def confirm_user(id):
    """Confirmar un usuario manualmente"""
    from datetime import datetime
    user = User.query.get_or_404(id)
    
    if user.confirmed_at:
        flash(_('Este usuario ya está confirmado'), 'warning')
        return redirect(url_for('admin.admin_users'))
    
    user.confirmed_at = datetime.utcnow()
    db.session.commit()
    
    current_app.logger.info(f'Admin {current_user.id} confirmed user {user.id}')
    flash(_('Usuario confirmado correctamente'), 'success')
    return redirect(url_for('admin.admin_users'))

@bp.route('/initiatives/pending')
@login_required
@roles_required('admin')
def pending_initiatives():
    """Lista de iniciativas pendientes de aprobación"""
    from flask import request
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get pending initiatives
    query = Initiative.query.filter(Initiative.status == 'pending')
    pagination = query.order_by(Initiative.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    initiatives = pagination.items
    
    # Statistics
    pending_count = Initiative.query.filter(Initiative.status == 'pending').count()
    approved_count = Initiative.query.filter(Initiative.status == 'approved').count()
    rejected_count = Initiative.query.filter(Initiative.status == 'rejected').count()
    
    return render_template('admin/pending_initiatives.html',
                         initiatives=initiatives,
                         pagination=pagination,
                         pending_count=pending_count,
                         approved_count=approved_count,
                         rejected_count=rejected_count)

@bp.route('/initiatives/<int:id>/approve', methods=['POST'])
@login_required
@roles_required('admin')
def approve_initiative(id):
    """Aprobar una iniciativa"""
    initiative = Initiative.query.get_or_404(id)
    
    if initiative.status != 'pending':
        flash(_('Esta iniciativa ya ha sido procesada'), 'warning')
        return redirect(url_for('admin.pending_initiatives'))
    
    initiative.status = 'approved'
    db.session.commit()
    
    # Send approval email
    try:
        from app.services.email_service import EmailService
        EmailService.send_initiative_approved(initiative, initiative.creator)
    except Exception as e:
        current_app.logger.error(f'Error sending initiative approval email: {str(e)}', exc_info=True)
    
    current_app.logger.info(f'{current_user.id} approved initiative {id}')
    flash(_('Iniciativa aprobada correctamente'), 'success')
    return redirect(url_for('admin.pending_initiatives', page=request.args.get('page', 1)))

@bp.route('/initiatives/<int:id>/reject', methods=['POST'])
@login_required
@roles_required('admin')
def reject_initiative(id):
    """Rechazar una iniciativa"""
    initiative = Initiative.query.get_or_404(id)
    
    if initiative.status != 'pending':
        flash(_('Esta iniciativa ya ha sido procesada'), 'warning')
        return redirect(url_for('admin.pending_initiatives'))
    
    initiative.status = 'rejected'
    reason = request.form.get('reason', None)
    db.session.commit()
    
    # Send rejection email
    try:
        from app.services.email_service import EmailService
        EmailService.send_initiative_rejected(initiative, initiative.creator, reason)
    except Exception as e:
        current_app.logger.error(f'Error sending initiative rejection email: {str(e)}', exc_info=True)
    
    current_app.logger.info(f'{current_user.id} rejected initiative {id}')
    flash(_('Iniciativa rechazada'), 'info')
    return redirect(url_for('admin.pending_initiatives', page=request.args.get('page', 1)))

@bp.route('/users/<int:id>/change-role', methods=['POST'])
@login_required
@roles_required('admin')
def change_user_role(id):
    """Cambiar el rol de un usuario"""
    from app.extensions import user_datastore
    from app.models import Role
    
    user = User.query.get_or_404(id)
    new_role_name = request.form.get('role')
    
    if not new_role_name:
        flash(_('Debes seleccionar un rol'), 'error')
        return redirect(url_for('admin.admin_users'))
    
    # No permitir cambiar el rol del admin actual
    if user.id == current_user.id and 'admin' in [r.name for r in user.roles]:
        flash(_('No puedes cambiar tu propio rol de administrador'), 'error')
        return redirect(url_for('admin.admin_users'))
    
    new_role = Role.query.filter_by(name=new_role_name).first()
    if not new_role:
        flash(_('Rol no válido'), 'error')
        return redirect(url_for('admin.admin_users'))
    
    # Remover todos los roles actuales y asignar el nuevo
    user_datastore.remove_role_from_user(user, *user.roles)
    user_datastore.add_role_to_user(user, new_role)
    db.session.commit()
    
    current_app.logger.info(f'Admin {current_user.id} changed role of user {user.id} to {new_role_name}')
    flash(_('Rol actualizado correctamente'), 'success')
    return redirect(url_for('admin.admin_users'))

@bp.route('/donations')
@login_required
@roles_required('admin')
def admin_donations():
    """Lista de donaciones recibidas"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get donations with pagination
    query = Donation.query.order_by(Donation.created_at.desc())
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    donations = pagination.items
    
    # Statistics
    total_donations = Donation.query.filter(Donation.status == 'completed').count()
    total_donated = db.session.query(db.func.sum(Donation.amount)).filter(Donation.status == 'completed').scalar() or 0
    total_donated_euros = total_donated / 100 if total_donated else 0
    pending_donations = Donation.query.filter(Donation.status == 'pending').count()
    refunded_donations = Donation.query.filter(Donation.status == 'refunded').count()
    
    return render_template('admin/donations.html',
                         donations=donations,
                         pagination=pagination,
                         total_donations=total_donations,
                         total_donated_euros=total_donated_euros,
                         pending_donations=pending_donations,
                         refunded_donations=refunded_donations)

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
    
    # Send approval email if reporter exists
    if item.reporter:
        try:
            from app.services.email_service import EmailService
            EmailService.send_inventory_item_approved(item, item.reporter.email)
        except Exception as e:
            current_app.logger.error(f'Error sending inventory approval email: {str(e)}', exc_info=True)
    
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
    reason = request.form.get('reason', None)
    db.session.commit()
    
    # Send rejection email if reporter exists
    if item.reporter:
        try:
            from app.services.email_service import EmailService
            EmailService.send_inventory_item_rejected(item, item.reporter.email, reason)
        except Exception as e:
            current_app.logger.error(f'Error sending inventory rejection email: {str(e)}', exc_info=True)
    
    current_app.logger.info(f'Admin {current_user.id} rejected inventory item {item.id}')
    flash(_('Item rechazado'), 'info')
    # Redirect back to pending page with pagination (from form data or args)
    page = request.form.get('page', request.args.get('page', 1, type=int), type=int)
    per_page = request.form.get('per_page', request.args.get('per_page', 20, type=int), type=int)
    return redirect(url_for('inventory.admin_inventory', status='pending', page=page, per_page=per_page))

