from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_security import login_required, current_user
from flask_babel import gettext as _
from app.models import Initiative, Comment
from app.extensions import db
from app.utils import sanitize_html, get_category_name
from app.forms import InitiativeForm
from datetime import datetime

bp = Blueprint('initiatives', __name__)

@bp.route('/iniciatives')
def list_initiatives():
    """Lista todas las iniciativas con filtros"""
    # Get filter parameters
    category = request.args.get('category')
    status = request.args.get('status', 'active')
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # Build query
    query = Initiative.query
    
    # Only show approved initiatives to public
    query = query.filter(Initiative.status == 'approved')
    
    if status == 'upcoming':
        query = query.filter(Initiative.date >= datetime.now().date())
    elif status == 'past':
        query = query.filter(Initiative.date < datetime.now().date())
    
    if category:
        query = query.filter(Initiative.category == category)
    
    # Pagination
    pagination = query.order_by(Initiative.date.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    initiatives = pagination.items
    
    # Get statistics
    total_initiatives = Initiative.query.filter(Initiative.status == 'approved').count()
    
    # Count participants (from user_initiatives association)
    from app.models import user_initiatives
    total_participants = db.session.query(db.func.count(db.func.distinct(user_initiatives.c.user_id))).scalar() or 0
    
    # Get categories for filter
    categories = db.session.query(Initiative.category).filter(
        Initiative.status == 'approved'
    ).distinct().all()
    category_list = [cat[0] for cat in categories]
    
    return render_template('initiatives/list.html',
                         initiatives=initiatives,
                         pagination=pagination,
                         total_initiatives=total_initiatives,
                         total_participants=total_participants,
                         categories=category_list,
                         selected_category=category,
                         selected_status=status,
                         get_category_name=get_category_name)

@bp.route('/initiative/create', methods=['GET', 'POST'])
@login_required
def create_initiative():
    """Permitir a usuarios crear iniciativas (requiere aprobación)"""
    from flask import current_app
    from app.utils import allowed_file, optimize_image
    from werkzeug.utils import secure_filename
    import os
    
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
            creator_id=current_user.id,
            status='pending'  # Requires approval
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
                    
                    # Upload to storage (S3 or local)
                    try:
                        from app.storage import get_storage
                        storage = get_storage()
                        storage_provider = current_app.config.get('STORAGE_PROVIDER', 'local').lower()
                        
                        current_app.logger.info(f'📤 Uploading initiative image to storage (provider={storage_provider}): {filename}')
                        storage.save(filename, file_path)
                        current_app.logger.info(f'✅ Initiative image uploaded to storage: {filename}')
                        
                        # If using S3, delete local file after upload
                        if storage_provider == 's3':
                            try:
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                    current_app.logger.info(f'🗑️ Deleted local file after S3 upload: {file_path}')
                            except Exception as e:
                                current_app.logger.warning(f'⚠️ Could not delete local file {file_path}: {e}')
                    except Exception as e:
                        current_app.logger.error(f'❌ Error uploading initiative image to storage: {e}', exc_info=True)
        
        db.session.add(initiative)
        db.session.commit()
        
        flash(_('Tu iniciativa ha sido creada y está pendiente de aprobación. Te notificaremos cuando sea revisada.'), 'success')
        return redirect(url_for('main.index'))
    
    return render_template('initiatives/create.html', form=form)

@bp.route('/initiative/<slug>')
def initiative_detail(slug):
    from flask import current_app
    from flask_security import current_user
    
    initiative = Initiative.query.filter_by(slug=slug).first_or_404()
    
    # Only show approved initiatives to public, or if user is creator/admin/moderator
    if initiative.status != 'approved':
        if not current_user.is_authenticated:
            from flask import abort
            abort(404)
        # Check if user is creator, admin, or moderator
        is_creator = initiative.creator_id == current_user.id
        is_admin = current_user.has_role('admin')
        is_moderator = current_user.has_role('moderator')
        if not (is_creator or is_admin or is_moderator):
            from flask import abort
            abort(404)
    
    # Increment view count
    initiative.view_count += 1
    db.session.commit()
    current_app.logger.debug(f'Initiative viewed: {slug} (views: {initiative.view_count})')
    
    # Get comments
    comments = initiative.comments.order_by(Comment.created_at.desc()).limit(10).all()
    
    # Check if current user is participating
    is_participating = False
    if current_user.is_authenticated:
        is_participating = current_user in initiative.participants
    
    # Get related initiatives (only approved)
    related = Initiative.query.filter(
        Initiative.category == initiative.category,
        Initiative.id != initiative.id,
        Initiative.status == 'approved'
    ).limit(3).all()
    
    return render_template('initiative_detail.html',
                         initiative=initiative,
                         comments=comments,
                         is_participating=is_participating,
                         related_initiatives=related)

@bp.route('/join/<slug>', methods=['POST'])
@login_required
def join_initiative(slug):
    """Join an initiative - requires login"""
    initiative = Initiative.query.filter_by(slug=slug).first_or_404()
    
    if current_user not in initiative.participants:
        initiative.participants.append(current_user)
        db.session.commit()
        flash('¡Te has unido a esta iniciativa con éxito!', 'success')
    else:
        flash('Ya estás participando en esta iniciativa', 'info')
    
    return redirect(url_for('initiatives.initiative_detail', slug=slug))

@bp.route('/leave/<slug>', methods=['POST'])
@login_required
def leave_initiative(slug):
    initiative = Initiative.query.filter_by(slug=slug).first_or_404()
    
    if current_user in initiative.participants:
        initiative.participants.remove(current_user)
        db.session.commit()
        flash('Has abandonado esta iniciativa', 'info')
    
    return redirect(url_for('initiatives.initiative_detail', slug=slug))

@bp.route('/comment/<slug>', methods=['POST'])
@login_required
def add_comment(slug):
    initiative = Initiative.query.filter_by(slug=slug).first_or_404()
    content = request.form.get('content')
    
    if content:
        comment = Comment(
            content=sanitize_html(content),
            user_id=current_user.id,
            initiative_id=initiative.id
        )
        db.session.add(comment)
        db.session.commit()
        flash('Comentario añadido con éxito', 'success')
    
    return redirect(url_for('initiatives.initiative_detail', slug=slug))

