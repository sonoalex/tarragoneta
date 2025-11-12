from time import timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_babel import gettext as _
from app.extensions import db, csrf
import stripe
import os
from stripe._error import SignatureVerificationError

bp = Blueprint('donations', __name__, url_prefix='/donate')

@bp.route('', methods=['GET', 'POST'])
def donate():
    """Donation page with Stripe integration"""
    if request.method == 'POST':
        try:
            amount = int(float(request.form.get('amount', 0)) * 100)  # Convert to cents
            current_app.logger.info(f'Donation attempt: {amount/100}€ from {request.form.get("email", "anonymous")}')
            
            if amount < 100:  # Minimum 1€
                current_app.logger.warning(f'Donation rejected: amount too low ({amount/100}€)')
                flash(_('La cantidad mínima es 1€'), 'error')
                return redirect(url_for('donations.donate'))
            
            # Check if Stripe is configured
            stripe_secret_key = current_app.config.get('STRIPE_SECRET_KEY')
            if not stripe_secret_key:
                current_app.logger.error('Donation attempt but Stripe not configured')
                flash(_('El sistema de pagos no está configurado. Por favor, contacta con nosotros.'), 'error')
                return redirect(url_for('main.contact'))
            
            # Create Stripe Checkout Session
            stripe.api_key = stripe_secret_key
            
            # Get current user if authenticated
            from flask_security import current_user
            user_email = request.form.get('email') or (current_user.email if current_user.is_authenticated else None)
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': _('Donación a Tarragoneta'),
                            'description': _('Donación voluntaria para mantener la plataforma'),
                        },
                        'unit_amount': amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=url_for('donations.donate_success', _external=True),
                cancel_url=url_for('donations.donate', _external=True),
                customer_email=user_email,  # Pre-fill email if provided
                metadata={
                    'donation_type': 'voluntary',
                    'user_email': user_email or 'anonymous',
                }
            )
            
            current_app.logger.info(f'Stripe checkout session created: {checkout_session.id}')
            return redirect(checkout_session.url, code=303)
            
        except stripe.error.StripeError as e:
            current_app.logger.error(f'Stripe error: {str(e)}', exc_info=True)
            flash(_('Error al procesar el pago: {error}').format(error=str(e)), 'error')
            return redirect(url_for('donations.donate'))
        except Exception as e:
            current_app.logger.error(f'Unexpected error in donation: {str(e)}', exc_info=True)
            flash(_('Error inesperado. Por favor, inténtalo de nuevo.'), 'error')
            return redirect(url_for('donations.donate'))
    
    stripe_publishable_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY', '')
    return render_template('donate.html', stripe_publishable_key=stripe_publishable_key)

@bp.route('/success')
def donate_success():
    """Success page after donation"""
    return render_template('donate_success.html')

@bp.route('/webhook', methods=['POST'])
@csrf.exempt  # Stripe webhooks don't include CSRF tokens
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        # Get secret from environment (fresh load) or config
        endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET') or current_app.config.get('STRIPE_WEBHOOK_SECRET')
        
        if not endpoint_secret:
            current_app.logger.warning('Stripe webhook called but webhook secret not configured')
            return jsonify({'error': 'Webhook secret not configured'}), 400
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            current_app.logger.info(f'Stripe webhook received: {event["type"]}')
        except ValueError as e:
            # Invalid payload
            current_app.logger.error(f'Invalid Stripe webhook payload: {str(e)}', exc_info=True)
            return jsonify({'error': 'Invalid payload'}), 400
        except SignatureVerificationError as e:
            # Invalid signature
            current_app.logger.error(f'Invalid Stripe webhook signature: {str(e)}', exc_info=True)
            return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        current_app.logger.error(f'Error in webhook handler: {str(e)}', exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    
    # Handle the event
    event_type = event.get('type', 'unknown')
    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            session_id = session.get('id', 'unknown')
            amount_total = session.get('amount_total', 0)
            current_app.logger.info(f'Payment successful for session: {session_id}, amount: {amount_total/100}€')
            
            # Save donation to database
            from app.models import Donation
            from datetime import datetime
            
            try:
                # Check if donation already exists
                existing_donation = Donation.query.filter_by(stripe_session_id=session_id).first()
                if not existing_donation:
                    # Get email safely
                    customer_details = session.get('customer_details') or {}
                    metadata = session.get('metadata') or {}
                    email = customer_details.get('email') or metadata.get('user_email') or None
                    
                    donation = Donation(
                        amount=amount_total,
                        currency=session.get('currency', 'eur'),
                        email=email,
                        stripe_session_id=session_id,
                        stripe_payment_intent_id=session.get('payment_intent'),
                        status='completed',
                        donation_type=metadata.get('donation_type', 'voluntary'),
                        completed_at=datetime.utcnow()
                    )
                    
                    # Try to link to user if email matches
                    user = None
                    if donation.email:
                        from app.models import User
                        user = User.query.filter_by(email=donation.email).first()
                        if user:
                            donation.user_id = user.id
                    
                    db.session.add(donation)
                    db.session.commit()
                    current_app.logger.info(f'Donation saved: {donation.id} - {donation.amount_euros}€')
                    
                    # Send donation confirmation email
                    try:
                        from app.services.email_service import EmailService
                        EmailService.send_donation_confirmation(donation, user)
                    except Exception as e:
                        current_app.logger.error(f'Error sending donation confirmation email: {str(e)}', exc_info=True)
                else:
                    # Update existing donation
                    existing_donation.status = 'completed'
                    existing_donation.completed_at = datetime.now(timezone.utc)
                    if session.get('payment_intent'):
                        existing_donation.stripe_payment_intent_id = session.get('payment_intent')
                    db.session.commit()
                    current_app.logger.info(f'Donation updated: {existing_donation.id}')
            except Exception as e:
                current_app.logger.error(f'Error saving donation for session {session_id}: {str(e)}', exc_info=True)
                db.session.rollback()
                raise  # Re-raise to be caught by outer try/except
        
        elif event['type'] == 'payment_intent.succeeded':
            # Additional confirmation when payment intent succeeds
            payment_intent = event['data']['object']
            current_app.logger.info(f'Payment intent succeeded: {payment_intent["id"]}')
        
        elif event['type'] == 'payment_intent.created':
            # Log but don't process (will be handled by checkout.session.completed)
            payment_intent = event['data']['object']
            current_app.logger.debug(f'Payment intent created: {payment_intent["id"]}')
        
        elif event['type'] == 'charge.refunded':
            # Handle refunds
            charge = event['data']['object']
            from app.models import Donation
            donation = Donation.query.filter_by(stripe_payment_intent_id=charge.get('payment_intent')).first()
            if donation:
                donation.status = 'refunded'
                db.session.commit()
                current_app.logger.info(f'Donation refunded: {donation.id}')
        
        elif event['type'] == 'charge.succeeded':
            # Log but don't process (will be handled by checkout.session.completed)
            charge = event['data']['object']
            current_app.logger.debug(f'Charge succeeded: {charge["id"]}')
        
        elif event['type'] == 'charge.updated':
            # Log but don't process (informational only)
            charge = event['data']['object']
            current_app.logger.debug(f'Charge updated: {charge["id"]}')
        
        else:
            # Log unhandled events but don't fail
            current_app.logger.debug(f'Unhandled event type: {event["type"]}')
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        current_app.logger.error(f'Error processing webhook event {event_type}: {str(e)}', exc_info=True)
        db.session.rollback()
        # Still return 200 to prevent Stripe from retrying excessively, but log the error
        return jsonify({'status': 'error', 'message': str(e)}), 200

