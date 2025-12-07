"""
Analytics routes for generating reports and data exports
"""
from flask import Blueprint, render_template, request, jsonify, make_response, redirect, url_for, flash, session, current_app
from flask_security import login_required, current_user
from flask_security.decorators import roles_required
from flask_babel import gettext as _
from datetime import datetime, timedelta
import csv
import io
import json
import stripe
import os
import secrets
from app.models import InventoryItem, District, Section, Initiative, Participation, user_initiatives, ReportPurchase, InventoryItemStatus
from app.extensions import db
from sqlalchemy import func, and_

bp = Blueprint('analytics', __name__, url_prefix='/admin/analytics')
bp_public = Blueprint('reports', __name__, url_prefix='/reports')

@bp_public.route('/')
def public_reports():
    """Public page to view and purchase reports"""
    # Get basic statistics (public info only)
    total_items = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).count()
    
    total_initiatives = Initiative.query.filter(
        Initiative.status == 'approved'
    ).count()
    
    # Get report price
    report_price = current_app.config.get('REPORT_PRICE_EUROS', 1.0)
    
    return render_template('reports/public.html',
                         total_items=total_items,
                         total_initiatives=total_initiatives,
                         report_price=report_price)

@bp.route('/purchases')
@login_required
@roles_required('admin')
def report_purchases():
    """View all report purchases and revenue"""
    # Get all completed purchases
    purchases = ReportPurchase.query.filter(
        ReportPurchase.status == 'completed'
    ).order_by(ReportPurchase.completed_at.desc()).all()
    
    # Calculate statistics
    total_revenue = sum(p.amount_euros for p in purchases)
    total_purchases = len(purchases)
    
    # Group by report type
    by_type = {}
    for purchase in purchases:
        if purchase.report_type not in by_type:
            by_type[purchase.report_type] = {'count': 0, 'revenue': 0}
        by_type[purchase.report_type]['count'] += 1
        by_type[purchase.report_type]['revenue'] += purchase.amount_euros
    
    return render_template('admin/analytics_purchases.html',
                         purchases=purchases,
                         total_revenue=total_revenue,
                         total_purchases=total_purchases,
                         by_type=by_type)

@bp.route('/')
@login_required
@roles_required('admin')
def analytics_dashboard():
    """Main analytics dashboard with report options"""
    # Get basic statistics
    total_items = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).count()
    
    total_initiatives = Initiative.query.filter(
        Initiative.status == 'approved'
    ).count()
    
    # Get districts and sections
    districts = District.query.order_by(District.code).all()
    sections = Section.query.order_by(Section.district_code, Section.code).all()
    
    # Get date range options
    today = datetime.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    last_quarter = today - timedelta(days=90)
    
    return render_template('admin/analytics.html',
                         total_items=total_items,
                         total_initiatives=total_initiatives,
                         districts=districts,
                         sections=sections,
                         date_ranges={
                             'last_week': last_week,
                             'last_month': last_month,
                             'last_quarter': last_quarter,
                             'all_time': None
                         })

@bp.route('/inventory-by-zone')
@login_required
@roles_required('admin')
def inventory_by_zone():
    """Generate inventory report grouped by district and section"""
    district_id = request.args.get('district_id', type=int)
    section_id = request.args.get('section_id', type=int)
    category = request.args.get('category')
    subcategory = request.args.get('subcategory')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    format = request.args.get('format', 'html')  # 'html' or 'csv'
    
    # Build query
    query = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    )
    
    # Apply filters
    if district_id:
        query = query.join(Section).filter(Section.district_code == 
            District.query.filter_by(id=district_id).first().code)
    if section_id:
        query = query.filter(InventoryItem.section_id == section_id)
    if category:
        query = query.filter(InventoryItem.category == category)
    if subcategory:
        query = query.filter(InventoryItem.subcategory == subcategory)
    if date_from:
        query = query.filter(InventoryItem.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(InventoryItem.created_at <= datetime.strptime(date_to, '%Y-%m-%d'))
    
    items = query.all()
    
    # Group by district and section
    report_data = {}
    for item in items:
        section = item.section
        if not section:
            district_name = _("Sense secció")
            section_name = _("Sense secció")
            section_code = "N/A"
        else:
            district = section.district
            district_name = district.name if district else _("Districte {code}").format(code=section.district_code)
            section_name = section.name or _("Secció {code}").format(code=section.code)
            section_code = section.full_code
        
        if district_name not in report_data:
            report_data[district_name] = {}
        if section_code not in report_data[district_name]:
            report_data[district_name][section_code] = {
                'section_name': section_name,
                'items': [],
                'by_category': {},
                'total': 0
            }
        
        report_data[district_name][section_code]['items'].append(item)
        report_data[district_name][section_code]['total'] += 1
        
        cat_key = f"{item.category}->{item.subcategory}"
        report_data[district_name][section_code]['by_category'][cat_key] = \
            report_data[district_name][section_code]['by_category'].get(cat_key, 0) + 1
    
    if format == 'csv':
        return _export_inventory_csv(report_data, items)
    
    # Convert dict to list of tuples for Jinja2 compatibility
    report_data_list = []
    for district_name, sections_dict in report_data.items():
        sections_list = []
        for section_code, section_data in sections_dict.items():
            # Convert by_category dict to list of tuples
            by_category_list = list(section_data['by_category'].items())
            section_data_copy = dict(section_data)
            section_data_copy['by_category'] = by_category_list
            sections_list.append((section_code, section_data_copy))
        report_data_list.append((district_name, sections_list))
    
    # Get districts and sections for filter dropdowns
    districts = District.query.order_by(District.code).all()
    sections = Section.query.order_by(Section.district_code, Section.code).all()
    
    return render_template('admin/analytics_inventory_by_zone.html',
                         report_data=report_data_list,
                         total_items=len(items),
                         districts=districts,
                         sections=sections,
                         filters={
                             'district_id': district_id,
                             'section_id': section_id,
                             'category': category,
                             'subcategory': subcategory,
                             'date_from': date_from,
                             'date_to': date_to
                         })

def _export_inventory_csv(report_data, items):
    """Export inventory report to CSV"""
    from app.utils import get_inventory_category_name, get_inventory_subcategory_name
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        _('Districte'),
        _('Secció'),
        _('Codi Secció'),
        _('Categoria'),
        _('Subcategoria'),
        _('Descripció'),
        _('Adreça'),
        _('Latitud'),
        _('Longitud'),
        _('Importància'),
        _('Resolts'),
        _('Data Creació')
    ])
    
    # Write data
    for district_name, sections in report_data.items():
        for section_code, section_data in sections.items():
            for item in section_data['items']:
                writer.writerow([
                    district_name,
                    section_data['section_name'],
                    section_code,
                    get_inventory_category_name(item.category),
                    get_inventory_subcategory_name(item.subcategory),
                    item.description or '',
                    item.address or '',
                    item.latitude,
                    item.longitude,
                    item.importance_count,
                    item.resolved_count,
                    item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else ''
                ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=inventory_by_zone_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@bp.route('/trends')
@login_required
@roles_required('admin')
def trends():
    """Generate trends report showing inventory items over time"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    category = request.args.get('category')
    district_id = request.args.get('district_id', type=int)
    format = request.args.get('format', 'html')
    
    # Build query
    query = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    )
    
    if date_from:
        query = query.filter(InventoryItem.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(InventoryItem.created_at <= datetime.strptime(date_to, '%Y-%m-%d'))
    if category:
        query = query.filter(InventoryItem.category == category)
    if district_id:
        district = District.query.get(district_id)
        if district:
            query = query.join(Section).filter(Section.district_code == district.code)
    
    items = query.order_by(InventoryItem.created_at).all()
    
    # Group by date
    from app.utils import get_inventory_category_name
    trends_data = {}
    for item in items:
        date_key = item.created_at.date().isoformat() if item.created_at else 'unknown'
        if date_key not in trends_data:
            trends_data[date_key] = {
                'date': date_key,
                'total': 0,
                'by_category': {}
            }
        trends_data[date_key]['total'] += 1
        # Use translated category name for display
        cat_key = get_inventory_category_name(item.category)
        trends_data[date_key]['by_category'][cat_key] = \
            trends_data[date_key]['by_category'].get(cat_key, 0) + 1
    
    # Sort by date
    sorted_trends = sorted(trends_data.items())
    
    if format == 'csv':
        return _export_trends_csv(sorted_trends)
    
    return render_template('admin/analytics_trends.html',
                         trends_data=sorted_trends,
                         filters={
                             'date_from': date_from,
                             'date_to': date_to,
                             'category': category,
                             'district_id': district_id
                         })

def _export_trends_csv(trends_data):
    """Export trends report to CSV"""
    from app.utils import get_inventory_category_name
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        _('Data'),
        _('Total'),
        _('Coloms'),
        _('Brossa'),
        _('Altres')
    ])
    
    # Write data
    for date_key, data in trends_data:
        coloms_count = data['by_category'].get(get_inventory_category_name('palomas'), 0)
        brossa_count = data['by_category'].get(get_inventory_category_name('basura'), 0)
        writer.writerow([
            date_key,
            data['total'],
            coloms_count,
            brossa_count,
            data['total'] - coloms_count - brossa_count
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=trends_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@bp.route('/top-categories')
@login_required
@roles_required('admin')
def top_categories():
    """Report of most reported categories by zone"""
    district_id = request.args.get('district_id', type=int)
    format = request.args.get('format', 'html')
    
    # Build query
    query = db.session.query(
        InventoryItem.category,
        InventoryItem.subcategory,
        Section.district_code,
        Section.code,
        func.count(InventoryItem.id).label('count')
    ).join(
        Section, InventoryItem.section_id == Section.id, isouter=True
    ).filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).group_by(
        InventoryItem.category,
        InventoryItem.subcategory,
        Section.district_code,
        Section.code
    )
    
    if district_id:
        district = District.query.get(district_id)
        if district:
            query = query.filter(Section.district_code == district.code)
    
    results = query.all()
    
    # Organize data
    report_data = {}
    for category, subcategory, district_code, section_code, count in results:
        cat_key = f"{category}->{subcategory}"
        zone_key = f"{district_code}-{section_code}" if district_code and section_code else _("Sense secció")
        
        if cat_key not in report_data:
            report_data[cat_key] = {
                'category': category,
                'subcategory': subcategory,
                'total': 0,
                'by_zone': {}
            }
        
        report_data[cat_key]['total'] += count
        report_data[cat_key]['by_zone'][zone_key] = \
            report_data[cat_key]['by_zone'].get(zone_key, 0) + count
    
    # Sort by total
    sorted_data = sorted(report_data.items(), key=lambda x: x[1]['total'], reverse=True)
    
    if format == 'csv':
        return _export_top_categories_csv(sorted_data)
    
    # Get districts for filter dropdown
    districts = District.query.order_by(District.code).all()
    
    return render_template('admin/analytics_top_categories.html',
                         report_data=sorted_data,
                         districts=districts,
                         filters={'district_id': district_id})

def _export_top_categories_csv(report_data):
    """Export top categories report to CSV"""
    from app.utils import get_inventory_category_name, get_inventory_subcategory_name
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        _('Categoria'),
        _('Subcategoria'),
        _('Total'),
        _('Zones Afectades')
    ])
    
    # Write data
    for cat_key, data in report_data:
        zones_affected = len(data['by_zone'])
        writer.writerow([
            get_inventory_category_name(data['category']),
            get_inventory_subcategory_name(data['subcategory']),
            data['total'],
            zones_affected
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=top_categories_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@bp_public.route('/purchase', methods=['POST'])
@login_required
def purchase_report():
    """Initiate payment for a report download (public endpoint for logged-in users)"""
    report_type = request.form.get('report_type')  # 'inventory_by_zone', 'trends', 'top_categories'
    report_params_json = request.form.get('report_params', '{}')  # JSON string with filters
    
    if not report_type:
        flash(_('Tipus de report no especificat'), 'error')
        return redirect(url_for('reports.public_reports'))
    
    # Feature flag: If payment is disabled, generate download token directly
    payment_enabled = current_app.config.get('REPORTS_PAYMENT_ENABLED', False)
    if not payment_enabled:
        current_app.logger.info(f'Reports payment disabled - generating free download for {report_type}')
        # Generate download token directly without payment
        import secrets
        from app.models import ReportPurchase
        from datetime import datetime
        
        download_token = secrets.token_urlsafe(32)
        
        # Create completed purchase record (free)
        purchase = ReportPurchase(
            report_type=report_type,
            report_params=report_params_json,
            amount=0,  # Free
            email=current_user.email,
            stripe_session_id=f'free_{secrets.token_urlsafe(16)}',  # Dummy session ID
            status='completed',
            download_token=download_token,
            completed_at=datetime.utcnow(),
            user_id=current_user.id
        )
        db.session.add(purchase)
        db.session.commit()
        
        current_app.logger.info(f'Free report download generated: {report_type} - token: {download_token[:16]}...')
        # Redirect to download page
        return redirect(url_for('reports.download_purchased_report', token=download_token))
    
    # Payment is enabled - proceed with Stripe checkout
    # Check if Stripe is configured
    stripe_secret_key = current_app.config.get('STRIPE_SECRET_KEY')
    if not stripe_secret_key:
        flash(_('El sistema de pagos no està configurat. Si us plau, contacta amb nosaltres.'), 'error')
        return redirect(url_for('reports.public_reports'))
    
    # Get report price
    report_price_euros = current_app.config.get('REPORT_PRICE_EUROS', 1.0)
    amount_cents = int(report_price_euros * 100)
    
    # Get user email (user is authenticated due to @login_required)
    user_email = current_user.email
    
    try:
        stripe.api_key = stripe_secret_key
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': _('Descàrrega de Report - Tarracograf'),
                        'description': _('Report: {report_type}').format(report_type=report_type),
                    },
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('reports.report_purchase_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('reports.public_reports', _external=True),
            customer_email=user_email,
            metadata={
                'report_type': report_type,
                'report_params': report_params_json,
                'purchase_type': 'report_download',
            }
        )
        
        # Create pending purchase record
        purchase = ReportPurchase(
            report_type=report_type,
            report_params=report_params_json,
            amount=amount_cents,
            email=user_email,
            stripe_session_id=checkout_session.id,
            status='pending',
            user_id=current_user.id
        )
        db.session.add(purchase)
        db.session.commit()
        
        current_app.logger.info(f'Report purchase initiated: {report_type} - {checkout_session.id}')
        return redirect(checkout_session.url, code=303)
        
    except stripe.error.StripeError as e:
        current_app.logger.error(f'Stripe error in report purchase: {str(e)}', exc_info=True)
        flash(_('Error al processar el pagament: {error}').format(error=str(e)), 'error')
        return redirect(url_for('reports.public_reports'))
    except Exception as e:
        current_app.logger.error(f'Unexpected error in report purchase: {str(e)}', exc_info=True)
        flash(_('Error inesperat. Si us plau, torna-ho a intentar.'), 'error')
        return redirect(url_for('reports.public_reports'))

@bp_public.route('/purchase-success')
@login_required
def report_purchase_success():
    """Success page after report purchase"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash(_('Sessió de pagament no vàlida'), 'error')
        return redirect(url_for('reports.public_reports'))
    
    # Find the purchase
    purchase = ReportPurchase.query.filter_by(stripe_session_id=session_id).first()
    
    if not purchase:
        flash(_('Compra no trobada'), 'error')
        return redirect(url_for('reports.public_reports'))
    
    # Verify the purchase belongs to the current user
    if purchase.user_id != current_user.id:
        flash(_('No tens permís per accedir a aquesta compra'), 'error')
        return redirect(url_for('reports.public_reports'))
    
    # If payment is not yet completed, check with Stripe API as fallback
    # (webhook might not have processed yet)
    if purchase.status != 'completed':
        stripe_secret_key = current_app.config.get('STRIPE_SECRET_KEY')
        if stripe_secret_key:
            try:
                stripe.api_key = stripe_secret_key
                checkout_session = stripe.checkout.Session.retrieve(session_id)
                
                # If payment is completed in Stripe, update our database
                if checkout_session.payment_status == 'paid':
                    purchase.status = 'completed'
                    purchase.completed_at = datetime.utcnow()
                    purchase.stripe_payment_intent_id = checkout_session.payment_intent
                    
                    # Generate download token if not exists
                    if not purchase.download_token:
                        purchase.download_token = secrets.token_urlsafe(32)
                    
                    # Update email if available
                    if checkout_session.customer_details and checkout_session.customer_details.get('email'):
                        purchase.email = checkout_session.customer_details.get('email')
                    
                    db.session.commit()
                    current_app.logger.info(f'Report purchase completed via API check: {purchase.id} - {purchase.report_type}')
            except stripe.error.StripeError as e:
                current_app.logger.warning(f'Error checking Stripe session {session_id}: {str(e)}')
            except Exception as e:
                current_app.logger.error(f'Unexpected error checking Stripe session: {str(e)}', exc_info=True)
    
    # If payment is completed, ensure download token exists
    if purchase.status == 'completed' and not purchase.download_token:
        purchase.download_token = secrets.token_urlsafe(32)
        db.session.commit()
    
    return render_template('admin/analytics_purchase_success.html',
                         purchase=purchase,
                         download_url=url_for('reports.download_purchased_report', token=purchase.download_token) if purchase.download_token else None)

@bp_public.route('/download/<token>')
@login_required
def download_purchased_report(token):
    """Download a purchased report using secure token"""
    purchase = ReportPurchase.query.filter_by(download_token=token).first_or_404()
    
    # Security check 1: Verify the purchase belongs to the current user
    if purchase.user_id != current_user.id:
        current_app.logger.warning(f'Unauthorized download attempt: user {current_user.id} tried to download purchase {purchase.id} (owner: {purchase.user_id})')
        flash(_('No tens permís per descarregar aquest report'), 'error')
        return redirect(url_for('reports.public_reports'))
    
    # Security check 2: Verify the purchase is completed
    if purchase.status != 'completed':
        flash(_('Aquest report encara no està disponible per descarregar'), 'error')
        return redirect(url_for('reports.public_reports'))
    
    # Security check 3: Verify the purchase was completed (has completed_at timestamp)
    if not purchase.completed_at:
        flash(_('Aquest report encara no està disponible per descarregar'), 'error')
        return redirect(url_for('reports.public_reports'))
    
    # Parse report parameters (these are immutable - stored at purchase time)
    try:
        report_params = json.loads(purchase.report_params) if purchase.report_params else {}
    except:
        report_params = {}
    
    # Security check 4: Log the download for audit purposes
    purchase.downloaded_at = datetime.utcnow()
    db.session.commit()
    
    # Log download with all relevant info for audit trail
    current_app.logger.info(
        f'Report downloaded: purchase_id={purchase.id}, type={purchase.report_type}, '
        f'user_id={current_user.id}, params={purchase.report_params}, '
        f'completed_at={purchase.completed_at}, downloaded_at={purchase.downloaded_at}'
    )
    
    # Generate the report based on type
    # IMPORTANT: We use the EXACT parameters stored at purchase time (report_params)
    # This ensures the user gets exactly what they paid for, not a different time period
    if purchase.report_type == 'inventory_by_zone':
        # Recreate the query from params (stored at purchase time - immutable)
        query = InventoryItem.query.filter(
            InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
        )
        
        # Apply filters exactly as they were at purchase time
        if report_params.get('district_id'):
            district = District.query.get(report_params['district_id'])
            if district:
                query = query.join(Section).filter(Section.district_code == district.code)
        if report_params.get('section_id'):
            query = query.filter(InventoryItem.section_id == report_params['section_id'])
        if report_params.get('category'):
            query = query.filter(InventoryItem.category == report_params['category'])
        if report_params.get('subcategory'):
            query = query.filter(InventoryItem.subcategory == report_params['subcategory'])
        
        # CRITICAL: Use the exact date range from purchase time
        # This prevents users from downloading reports for different months
        if report_params.get('date_from'):
            date_from = datetime.strptime(report_params['date_from'], '%Y-%m-%d')
            query = query.filter(InventoryItem.created_at >= date_from)
        if report_params.get('date_to'):
            date_to = datetime.strptime(report_params['date_to'], '%Y-%m-%d')
            # Add 23:59:59 to include the entire end date
            date_to = date_to.replace(hour=23, minute=59, second=59)
            query = query.filter(InventoryItem.created_at <= date_to)
        
        items = query.all()
        
        # Build report_data (same structure as inventory_by_zone)
        report_data = {}
        for item in items:
            section = item.section
            if not section:
                district_name = _("Sense secció")
                section_name = _("Sense secció")
                section_code = "N/A"
            else:
                district = section.district
                district_name = district.name if district else _("Districte {code}").format(code=section.district_code)
                section_name = section.name or _("Secció {code}").format(code=section.code)
                section_code = section.full_code
            
            if district_name not in report_data:
                report_data[district_name] = {}
            if section_code not in report_data[district_name]:
                report_data[district_name][section_code] = {
                    'section_name': section_name,
                    'items': [],
                    'by_category': {},
                    'total': 0
                }
            
            report_data[district_name][section_code]['items'].append(item)
            report_data[district_name][section_code]['total'] += 1
            
            cat_key = f"{item.category}->{item.subcategory}"
            report_data[district_name][section_code]['by_category'][cat_key] = \
                report_data[district_name][section_code]['by_category'].get(cat_key, 0) + 1
        
        return _export_inventory_csv(report_data, items)
    
    elif purchase.report_type == 'trends':
        # Similar logic for trends - using exact params from purchase time
        query = InventoryItem.query.filter(
            InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
        )
        
        # CRITICAL: Use the exact date range from purchase time
        if report_params.get('date_from'):
            date_from = datetime.strptime(report_params['date_from'], '%Y-%m-%d')
            query = query.filter(InventoryItem.created_at >= date_from)
        if report_params.get('date_to'):
            date_to = datetime.strptime(report_params['date_to'], '%Y-%m-%d')
            # Add 23:59:59 to include the entire end date
            date_to = date_to.replace(hour=23, minute=59, second=59)
            query = query.filter(InventoryItem.created_at <= date_to)
        if report_params.get('category'):
            query = query.filter(InventoryItem.category == report_params['category'])
        if report_params.get('district_id'):
            district = District.query.get(report_params['district_id'])
            if district:
                query = query.join(Section).filter(Section.district_code == district.code)
        
        items = query.order_by(InventoryItem.created_at).all()
        
        from app.utils import get_inventory_category_name
        trends_data = {}
        for item in items:
            date_key = item.created_at.date().isoformat() if item.created_at else 'unknown'
            if date_key not in trends_data:
                trends_data[date_key] = {
                    'date': date_key,
                    'total': 0,
                    'by_category': {}
                }
            trends_data[date_key]['total'] += 1
            cat_key = get_inventory_category_name(item.category)
            trends_data[date_key]['by_category'][cat_key] = \
                trends_data[date_key]['by_category'].get(cat_key, 0) + 1
        
        sorted_trends = sorted(trends_data.items())
        return _export_trends_csv(sorted_trends)
    
    elif purchase.report_type == 'top_categories':
        # Similar logic for top_categories
        query = db.session.query(
            InventoryItem.category,
            InventoryItem.subcategory,
            Section.district_code,
            Section.code,
            func.count(InventoryItem.id).label('count')
        ).join(
            Section, InventoryItem.section_id == Section.id, isouter=True
        ).filter(
            InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
        ).group_by(
            InventoryItem.category,
            InventoryItem.subcategory,
            Section.district_code,
            Section.code
        )
        
        if report_params.get('district_id'):
            district = District.query.get(report_params['district_id'])
            if district:
                query = query.filter(Section.district_code == district.code)
        
        results = query.all()
        
        report_data = {}
        for category, subcategory, district_code, section_code, count in results:
            cat_key = f"{category}->{subcategory}"
            zone_key = f"{district_code}-{section_code}" if district_code and section_code else "Sense secció"
            
            if cat_key not in report_data:
                report_data[cat_key] = {
                    'category': category,
                    'subcategory': subcategory,
                    'total': 0,
                    'by_zone': {}
                }
            
            report_data[cat_key]['total'] += count
            report_data[cat_key]['by_zone'][zone_key] = \
                report_data[cat_key]['by_zone'].get(zone_key, 0) + count
        
        sorted_data = sorted(report_data.items(), key=lambda x: x[1]['total'], reverse=True)
        return _export_top_categories_csv(sorted_data)
    
    flash(_('Tipus de report no vàlid'), 'error')
    return redirect(url_for('reports.public_reports'))

@bp_public.route('/inventory-by-zone')
def view_inventory_by_zone():
    """Public preview of inventory by zone report (statistics only)"""
    from app.utils import get_inventory_category_name, get_inventory_subcategory_name
    
    # Get basic statistics (no filters for preview)
    items = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).all()
    
    # Calculate summary statistics
    total_items = len(items)
    by_district = {}
    by_category = {}
    by_section = {}
    
    for item in items:
        # By district
        if item.section and item.section.district:
            district_name = item.section.district.name or f"Districte {item.section.district_code}"
            by_district[district_name] = by_district.get(district_name, 0) + 1
        
        # By category
        cat_name = get_inventory_category_name(item.category)
        by_category[cat_name] = by_category.get(cat_name, 0) + 1
        
        # By section (top 10)
        if item.section:
            section_name = item.section.name or f"Secció {item.section.code}"
            section_key = f"{item.section.district_code}-{item.section.code}"
            by_section[section_key] = {
                'name': section_name,
                'district': item.section.district.name if item.section.district else item.section.district_code,
                'count': by_section.get(section_key, {}).get('count', 0) + 1
            }
    
    # Sort and limit
    top_districts = sorted(by_district.items(), key=lambda x: x[1], reverse=True)[:10]
    top_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    top_sections = sorted(by_section.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
    
    return render_template('reports/preview_inventory_by_zone.html',
                         total_items=total_items,
                         top_districts=top_districts,
                         top_categories=top_categories,
                         top_sections=top_sections,
                         payment_enabled=current_app.config.get('REPORTS_PAYMENT_ENABLED', False))

@bp_public.route('/trends')
def view_trends():
    """Public preview of trends report (statistics only)"""
    from app.utils import get_inventory_category_name
    
    # Get items from last 6 months
    six_months_ago = datetime.now() - timedelta(days=180)
    items = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses()),
        InventoryItem.created_at >= six_months_ago
    ).order_by(InventoryItem.created_at).all()
    
    # Group by month
    by_month = {}
    by_category_monthly = {}
    
    for item in items:
        month_key = item.created_at.strftime('%Y-%m') if item.created_at else 'unknown'
        by_month[month_key] = by_month.get(month_key, 0) + 1
        
        cat_name = get_inventory_category_name(item.category)
        if month_key not in by_category_monthly:
            by_category_monthly[month_key] = {}
        by_category_monthly[month_key][cat_name] = by_category_monthly[month_key].get(cat_name, 0) + 1
    
    # Sort by month
    sorted_months = sorted(by_month.items())
    
    return render_template('reports/preview_trends.html',
                         monthly_data=sorted_months,
                         category_monthly=by_category_monthly,
                         total_items=len(items),
                         payment_enabled=current_app.config.get('REPORTS_PAYMENT_ENABLED', False))

@bp_public.route('/top-categories')
def view_top_categories():
    """Public preview of top categories report (statistics only)"""
    from app.utils import get_inventory_category_name, get_inventory_subcategory_name
    
    # Get aggregated data
    results = db.session.query(
        InventoryItem.category,
        InventoryItem.subcategory,
        func.count(InventoryItem.id).label('count')
    ).filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).group_by(
        InventoryItem.category,
        InventoryItem.subcategory
    ).order_by(func.count(InventoryItem.id).desc()).all()
    
    # Organize data
    top_categories = []
    for category, subcategory, count in results[:20]:  # Top 20
        top_categories.append({
            'category': get_inventory_category_name(category),
            'subcategory': get_inventory_subcategory_name(subcategory),
            'count': count
        })
    
    # Total items
    total_items = InventoryItem.query.filter(
        InventoryItem.status.in_(InventoryItemStatus.visible_statuses())
    ).count()
    
    return render_template('reports/preview_top_categories.html',
                         top_categories=top_categories,
                         total_items=total_items,
                         payment_enabled=current_app.config.get('REPORTS_PAYMENT_ENABLED', False))

