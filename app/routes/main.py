from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_babel import gettext as _
from app.models import Initiative, Comment, user_initiatives, InventoryItem, InventoryItemStatus
from app.extensions import db
from datetime import datetime
from sqlalchemy import not_

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Get filter parameters for initiatives
    category = request.args.get('category')
    status = request.args.get('status', 'active')
    
    # Build query for initiatives
    query = Initiative.query
    
    # Only show approved initiatives to public
    query = query.filter(Initiative.status == 'approved')
    
    if status == 'upcoming':
        query = query.filter(Initiative.date >= datetime.now().date())
    elif status == 'past':
        query = query.filter(Initiative.date < datetime.now().date())
    
    if category:
        query = query.filter(Initiative.category == category)
    
    initiatives = query.order_by(Initiative.date.asc()).limit(6).all()  # Limit to 6 for homepage
    
    # Get inventory statistics (for hero section)
    # Exclude 'escombreries_desbordades' - now handled by Container Points
    total_inventory_items = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).filter(
        not_((InventoryItem.category == 'basura') & 
             (InventoryItem.subcategory.in_(['escombreries_desbordades', 'basura_desbordada'])))
    ).count()
    
    # Get inventory by category
    inventory_by_category = {}
    for item in InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).filter(
        not_((InventoryItem.category == 'basura') & 
             (InventoryItem.subcategory.in_(['escombreries_desbordades', 'basura_desbordada'])))
    ).all():
        inventory_by_category[item.category] = inventory_by_category.get(item.category, 0) + 1
    
    # Get recent inventory items (for featured section)
    recent_inventory_items = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).filter(
        not_((InventoryItem.category == 'basura') & 
             (InventoryItem.subcategory.in_(['escombreries_desbordades', 'basura_desbordada'])))
    ).order_by(InventoryItem.created_at.desc()).limit(8).all()
    
    # Get statistics for initiatives (for secondary section)
    total_initiatives = Initiative.query.filter(Initiative.status == 'approved').count()
    total_participants = db.session.query(db.func.count(user_initiatives.c.user_id)).scalar() or 0
    active_categories = db.session.query(Initiative.category).distinct().count()
    
    return render_template('index.html',
                         initiatives=initiatives,
                         total_initiatives=total_initiatives,
                         total_participants=total_participants,
                         active_categories=active_categories,
                         selected_category=category,
                         selected_status=status,
                         total_inventory_items=total_inventory_items,
                         inventory_by_category=inventory_by_category,
                         recent_inventory_items=recent_inventory_items)

@bp.route('/about')
def about():
    return render_template('about.html')

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    from flask import current_app
    if request.method == 'POST':
        # Check for duplicate submission using session token
        form_token = request.form.get('form_token', '')
        session_token = session.get('contact_form_token')
        
        # If tokens match, it's a valid first submission
        # If they don't match (or token is missing), it could be a duplicate or invalid
        if form_token and form_token == session_token:
            # Valid submission - process it and generate new token
            # Generate new token AFTER processing to prevent duplicates
            import secrets
            new_token = secrets.token_hex(16)
            session['contact_form_token'] = new_token
        elif form_token and session_token:
            # Token mismatch - likely a duplicate submission
            current_app.logger.info(f'Duplicate contact form submission prevented from {request.form.get("email", "unknown")}')
            flash(_('El formulari ja s\'ha enviat. Si us plau, espera uns segons.'), 'info')
            return redirect(url_for('main.contact'))
        else:
            # No token in form or session - generate new one and allow submission
            # (could be first time or session expired)
            import secrets
            new_token = secrets.token_hex(16)
            session['contact_form_token'] = new_token
        
        # Get form data
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        subject = request.form.get('subject', '')
        message = request.form.get('message', '')
        phone = request.form.get('phone', '')
        
        # Validate required fields
        if not name or not email or not message:
            flash(_('Si us plau, omple tots els camps obligatoris'), 'error')
            return redirect(url_for('main.contact'))
        
        # Log contact form submission
        current_app.logger.info(f'Contact form submitted: {subject} from {email} ({name})')
        
        # Send confirmation email to user (only if email is different from admin)
        admin_email = current_app.config.get('ADMIN_EMAIL', 'hola@tarracograf.cat')
        if email and email.lower() != admin_email.lower():
            try:
                from app.services.email_service import EmailService
                EmailService.send_contact_form_response(email, subject, message)
            except Exception as e:
                current_app.logger.error(f'Error sending contact confirmation email: {str(e)}', exc_info=True)
        
        # Send notification to admin
        if admin_email:
            try:
                from app.services.email_service import EmailService
                current_app.logger.info(f'Sending admin notification to {admin_email} for contact form from {email}')
                result = EmailService.send_admin_notification(
                    admin_email,
                    'Nou missatge de contacte',
                    {
                        'name': name,
                        'email': email,
                        'subject': subject,
                        'message': message,
                        'phone': phone if phone else 'No proporcionat'
                    }
                )
                if result:
                    current_app.logger.info(f'Admin notification email sent successfully to {admin_email}')
                else:
                    current_app.logger.warning(f'Admin notification email failed to send to {admin_email}')
            except Exception as e:
                current_app.logger.error(f'Error sending admin notification: {str(e)}', exc_info=True)
        
        flash(_('Gràcies pel teu missatge. Et respondrem aviat.'), 'success')
        return redirect(url_for('main.contact'))
    
    # Generate form token for GET request (to prevent double submission)
    if 'contact_form_token' not in session:
        import secrets
        session['contact_form_token'] = secrets.token_hex(16)
    
    # Get subject from query parameter (for donation banner)
    subject_param = request.args.get('subject', '')
    return render_template('contact.html', default_subject=subject_param)

@bp.route('/confirm-email/<token>')
def confirm_email(token):
    """Confirm user email with token from welcome email"""
    from app.models import User
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
    
    try:
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = serializer.loads(
            token,
            salt=current_app.config.get('SECURITY_PASSWORD_SALT', 'tarracograf-salt-2024'),
            max_age=86400 * 7  # Token válido por 7 días
        )
        
        user = User.query.filter_by(email=email).first_or_404()
        
        if user.confirmed_at:
            flash(_('El teu correu electrònic ja està confirmat.'), 'info')
            return redirect(url_for('security.login'))
        
        # Confirm user
        user.confirmed_at = datetime.utcnow()
        db.session.commit()
        
        current_app.logger.info(f'User {user.id} ({user.email}) confirmed email via token')
        flash(_('Correu electrònic confirmat correctament! Ja pots iniciar sessió.'), 'success')
        return redirect(url_for('security.login'))
        
    except SignatureExpired:
        flash(_('El enllaç de confirmació ha expirat. Si us plau, contacta amb l\'administrador o sol·licita un nou enllaç.'), 'error')
        return redirect(url_for('main.contact'))
    except BadSignature:
        flash(_('El enllaç de confirmació no és vàlid. Si us plau, contacta amb l\'administrador.'), 'error')
        return redirect(url_for('main.contact'))
    except Exception as e:
        current_app.logger.error(f'Error confirming email: {str(e)}', exc_info=True)
        flash(_('Hi ha hagut un error al confirmar el correu. Si us plau, contacta amb l\'administrador.'), 'error')
        return redirect(url_for('main.contact'))

@bp.route('/set_language/<lang>')
def set_language(lang):
    from flask import current_app
    
    if lang in current_app.config['BABEL_SUPPORTED_LOCALES']:
        session['language'] = lang
        session.permanent = True
        session.modified = True
    return redirect(request.referrer or url_for('main.index'))

