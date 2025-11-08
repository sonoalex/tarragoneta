from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_babel import gettext as _
import stripe

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
                metadata={
                    'donation_type': 'voluntary',
                    'user_email': request.form.get('email', 'anonymous'),
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
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
    
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
        current_app.logger.error(f'Invalid Stripe webhook payload: {str(e)}')
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        current_app.logger.error(f'Invalid Stripe webhook signature: {str(e)}')
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        current_app.logger.info(f'Payment successful for session: {session["id"]}, amount: {session.get("amount_total", 0)/100}€')
        # TODO: Save donation to database if needed
    
    return jsonify({'status': 'success'}), 200

