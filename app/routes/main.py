from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_babel import gettext as _
from app.models import Initiative, Comment, Participation, user_initiatives
from app.extensions import db
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Get filter parameters
    category = request.args.get('category')
    status = request.args.get('status', 'active')
    
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
    
    initiatives = query.order_by(Initiative.date.asc()).all()
    
    # Get statistics
    total_initiatives = Initiative.query.count()
    total_participants = db.session.query(db.func.count(user_initiatives.c.user_id)).scalar() or 0
    total_participants += Participation.query.count()
    active_categories = db.session.query(Initiative.category).distinct().count()
    
    return render_template('index.html',
                         initiatives=initiatives,
                         total_initiatives=total_initiatives,
                         total_participants=total_participants,
                         active_categories=active_categories,
                         selected_category=category,
                         selected_status=status)

@bp.route('/about')
def about():
    return render_template('about.html')

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    from flask import current_app
    if request.method == 'POST':
        # Handle contact form submission
        current_app.logger.info(f'Contact form submitted: {request.form.get("subject", "unknown")} from {request.form.get("email", "anonymous")}')
        flash('Gracias por tu mensaje. Te responderemos pronto.', 'success')
        return redirect(url_for('main.contact'))
    
    # Get subject from query parameter (for donation banner)
    subject_param = request.args.get('subject', '')
    return render_template('contact.html', default_subject=subject_param)

@bp.route('/set_language/<lang>')
def set_language(lang):
    from flask import current_app
    
    if lang in current_app.config['BABEL_SUPPORTED_LOCALES']:
        session['language'] = lang
        session.permanent = True
        session.modified = True
    return redirect(request.referrer or url_for('main.index'))

