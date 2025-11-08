from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_security import login_required, current_user
from flask_babel import gettext as _
from app.models import Initiative, Comment, Participation
from app.extensions import db
from app.utils import sanitize_html
from datetime import datetime

bp = Blueprint('initiatives', __name__)

@bp.route('/initiative/<slug>')
def initiative_detail(slug):
    from flask import current_app
    initiative = Initiative.query.filter_by(slug=slug).first_or_404()
    
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
    
    # Get related initiatives
    related = Initiative.query.filter(
        Initiative.category == initiative.category,
        Initiative.id != initiative.id,
        Initiative.status == 'active'
    ).limit(3).all()
    
    return render_template('initiative_detail.html',
                         initiative=initiative,
                         comments=comments,
                         is_participating=is_participating,
                         related_initiatives=related)

@bp.route('/join/<slug>', methods=['POST'])
def join_initiative(slug):
    initiative = Initiative.query.filter_by(slug=slug).first_or_404()
    
    if current_user.is_authenticated:
        # Registered user participation
        if current_user not in initiative.participants:
            initiative.participants.append(current_user)
            db.session.commit()
            flash('¡Te has unido a esta iniciativa con éxito!', 'success')
        else:
            flash('Ya estás participando en esta iniciativa', 'info')
    else:
        # Anonymous participation
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        if not name:
            flash('El nombre es obligatorio', 'error')
            return redirect(url_for('initiatives.initiative_detail', slug=slug))
        
        participation = Participation(
            initiative_id=initiative.id,
            name=sanitize_html(name),
            email=sanitize_html(email) if email else None,
            phone=sanitize_html(phone) if phone else None
        )
        db.session.add(participation)
        db.session.commit()
        flash('¡Te has registrado en esta iniciativa! Te contactaremos pronto.', 'success')
    
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

