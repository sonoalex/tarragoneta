"""
Email service for Tarragoneta
Handles all email sending with consistent styling
Supports both synchronous and asynchronous (queue) sending
"""
from flask import render_template, current_app, url_for, copy_current_request_context
from flask_mail import Message
from flask_babel import gettext as _
from app.extensions import mail, email_queue, redis_conn
from datetime import datetime
import functools


def send_email_task(to, subject, template, **kwargs):
    """
    Task function for RQ worker (must be at module level for RQ to import it)
    This function is called by the worker to send emails
    """
    from app import create_app
    app = create_app()
    
    # Create a request context for URL generation
    with app.app_context():
        # Push a request context to allow url_for with _external=True
        with app.test_request_context():
            return EmailService._send_email_sync(to, subject, template, **kwargs)


class EmailService:
    """Service for sending emails with Tarragoneta branding"""
    
    @staticmethod
    def _send_email_sync(to, subject, template, **kwargs):
        """
        Internal method to send email synchronously (used by queue worker)
        
        Args:
            to: Email address or list of addresses
            subject: Email subject
            template: Template name (without .html)
            **kwargs: Additional context variables for the template (may contain serialized objects)
        """
        # Log mail configuration status
        mail_suppress = current_app.config.get('MAIL_SUPPRESS_SEND', False)
        mail_server = current_app.config.get('MAIL_SERVER', 'not set')
        mail_username = current_app.config.get('MAIL_USERNAME', 'not set')
        mail_password_set = bool(current_app.config.get('MAIL_PASSWORD', ''))
        
        current_app.logger.info(f'[EMAIL DEBUG] Suppress: {mail_suppress}, Server: {mail_server}, Username: {mail_username}, Password: {"set" if mail_password_set else "NOT SET"}')
        
        if mail_suppress:
            current_app.logger.info(f'[EMAIL SUPPRESSED] To: {to}, Subject: {subject}')
            return True
        
        try:
            # Deserialize kwargs (convert IDs back to objects if needed)
            deserialized_kwargs = EmailService._deserialize_kwargs(kwargs)
            
            # Add recipient_email to template context
            recipient_email = to if isinstance(to, str) else ', '.join(to)
            deserialized_kwargs['recipient_email'] = recipient_email
            
            current_app.logger.info(f'[EMAIL DEBUG] Creating message for {to}...')
            msg = Message(
                subject=subject,
                recipients=[to] if isinstance(to, str) else to,
                html=render_template(f'emails/{template}.html', **deserialized_kwargs),
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'Tarragoneta <hola@tarragoneta.com>')
            )
            
            current_app.logger.info(f'[EMAIL DEBUG] Sending email to {to}...')
            mail.send(msg)
            current_app.logger.info(f'Email sent successfully to {to}: {subject}')
            return True
        except Exception as e:
            current_app.logger.error(f'Error sending email to {to}: {str(e)}', exc_info=True)
            return False
    
    @staticmethod
    def send_email(to, subject, template, **kwargs):
        """
        Send an email using a template (queued if Redis is available)
        
        Args:
            to: Email address or list of addresses
            subject: Email subject
            template: Template name (without .html)
            **kwargs: Additional context variables for the template
        """
        use_queue = current_app.config.get('USE_EMAIL_QUEUE', True)
        
        # If queue is enabled and available, use it
        if use_queue and email_queue and redis_conn:
            try:
                # Serialize kwargs (convert objects to IDs if needed)
                serialized_kwargs = EmailService._serialize_kwargs(kwargs)
                
                # Enqueue the email job
                # Use the module-level function that RQ can import
                job = email_queue.enqueue(
                    'app.services.email_service.send_email_task',
                    to, subject, template,
                    **serialized_kwargs,
                    job_timeout=300  # 5 minutes timeout
                )
                current_app.logger.info(f'Email queued for {to}: {subject} (Job ID: {job.id})')
                return True
            except Exception as e:
                current_app.logger.warning(f'Failed to queue email, sending synchronously: {str(e)}')
                # Fallback to synchronous sending
                return EmailService._send_email_sync(to, subject, template, **kwargs)
        else:
            # Send synchronously if queue is disabled or unavailable
            return EmailService._send_email_sync(to, subject, template, **kwargs)
    
    @staticmethod
    def _serialize_kwargs(kwargs):
        """
        Serialize kwargs for queue (convert model objects to IDs and URLs to strings)
        """
        serialized = {}
        for key, value in kwargs.items():
            # Skip None values
            if value is None:
                continue
            # If it's a model instance, convert to ID
            elif hasattr(value, 'id'):
                serialized[f'{key}_id'] = value.id
                serialized[f'{key}_type'] = value.__class__.__name__
            # If it's a datetime, convert to ISO string
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            # If it's a URL (from url_for), it's already a string
            elif isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                serialized[key] = value
            # Otherwise, keep as is (strings, numbers, etc.)
            else:
                serialized[key] = value
        return serialized
    
    @staticmethod
    def _deserialize_kwargs(kwargs):
        """
        Deserialize kwargs from queue (convert IDs back to model objects)
        """
        from app.models import User, Donation, Initiative, InventoryItem
        
        deserialized = {}
        model_map = {
            'User': User,
            'Donation': Donation,
            'Initiative': Initiative,
            'InventoryItem': InventoryItem
        }
        
        # Track which keys we've processed
        processed_keys = set()
        
        for key, value in kwargs.items():
            # Check if this is a serialized object (has _id and _type)
            if key.endswith('_id'):
                base_key = key[:-3]  # Remove '_id'
                type_key = f'{base_key}_type'
                
                if type_key in kwargs:
                    model_name = kwargs[type_key]
                    if model_name in model_map:
                        model_class = model_map[model_name]
                        try:
                            obj = model_class.query.get(value)
                            if obj:
                                deserialized[base_key] = obj
                                processed_keys.add(key)
                                processed_keys.add(type_key)
                        except Exception as e:
                            current_app.logger.warning(f'Could not deserialize {base_key}: {str(e)}')
                            deserialized[base_key] = None
                            processed_keys.add(key)
                            processed_keys.add(type_key)
                else:
                    # Just an ID without type, keep as is
                    deserialized[key] = value
            elif key.endswith('_type'):
                # Skip type keys (already processed with _id)
                if key not in processed_keys:
                    processed_keys.add(key)
            else:
                # Regular value, keep as is
                deserialized[key] = value
        
        return deserialized
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email after registration"""
        return EmailService.send_email(
            to=user.email,
            subject=_('Benvingut/da a Tarragoneta! 🌱'),
            template='welcome',
            user=user,
            login_url=url_for('security.login', _external=True)
        )
    
    @staticmethod
    def send_donation_confirmation(donation, user=None):
        """Send donation confirmation email"""
        recipient = donation.email or (user.email if user else None)
        if not recipient:
            current_app.logger.warning('No email address for donation confirmation')
            return False
        
        return EmailService.send_email(
            to=recipient,
            subject=_('Gràcies per la teva donació! 💚'),
            template='donation_confirmation',
            donation=donation,
            user=user,
            amount=donation.amount_euros if hasattr(donation, 'amount_euros') else None
        )
    
    @staticmethod
    def send_initiative_approved(initiative, user):
        """Send email when initiative is approved"""
        try:
            initiative_url = url_for('initiatives.detail', id=initiative.id, _external=True)
        except:
            initiative_url = None
        return EmailService.send_email(
            to=user.email,
            subject=_('La teva iniciativa ha estat aprovada! ✅'),
            template='initiative_approved',
            initiative=initiative,
            user=user,
            initiative_url=initiative_url
        )
    
    @staticmethod
    def send_initiative_rejected(initiative, user, reason=None):
        """Send email when initiative is rejected"""
        return EmailService.send_email(
            to=user.email,
            subject=_('Informació sobre la teva iniciativa'),
            template='initiative_rejected',
            initiative=initiative,
            user=user,
            reason=reason
        )
    
    @staticmethod
    def send_initiative_reminder(initiative, user):
        """Send reminder email before initiative date"""
        try:
            initiative_url = url_for('initiatives.detail', id=initiative.id, _external=True)
        except:
            initiative_url = None
        return EmailService.send_email(
            to=user.email,
            subject=_('Recordatori: La teva iniciativa és demà! 📅'),
            template='initiative_reminder',
            initiative=initiative,
            user=user,
            initiative_url=initiative_url
        )
    
    @staticmethod
    def send_participant_confirmation(initiative, participant_email, participant_name=None):
        """Send confirmation email to initiative participant"""
        try:
            initiative_url = url_for('initiatives.detail', id=initiative.id, _external=True)
        except:
            initiative_url = None
        return EmailService.send_email(
            to=participant_email,
            subject=_('Confirmació de participació en iniciativa'),
            template='participant_confirmation',
            initiative=initiative,
            participant_name=participant_name,
            initiative_url=initiative_url
        )
    
    @staticmethod
    def send_inventory_item_approved(item, reporter_email):
        """Send email when inventory item is approved"""
        try:
            item_url = url_for('inventory.inventory_map', category=item.category, subcategory=item.subcategory, _external=True)
        except:
            item_url = None
        return EmailService.send_email(
            to=reporter_email,
            subject=_('El teu reportatge ha estat aprovat! ✅'),
            template='inventory_approved',
            item=item,
            item_url=item_url
        )
    
    @staticmethod
    def send_inventory_item_rejected(item, reporter_email, reason=None):
        """Send email when inventory item is rejected"""
        return EmailService.send_email(
            to=reporter_email,
            subject=_('Informació sobre el teu reportatge'),
            template='inventory_rejected',
            item=item,
            reason=reason
        )
    
    @staticmethod
    def send_contact_form_response(contact_email, subject, message):
        """Send response to contact form submission"""
        return EmailService.send_email(
            to=contact_email,
            subject=_('Gràcies per contactar amb Tarragoneta'),
            template='contact_response',
            contact_email=contact_email,
            contact_subject=subject,  # Renamed to avoid conflict with email subject
            message=message
        )
    
    @staticmethod
    def send_admin_notification(admin_email, notification_type, data):
        """Send notification to admin"""
        return EmailService.send_email(
            to=admin_email,
            subject=_('Notificació de Tarragoneta'),
            template='admin_notification',
            notification_type=notification_type,
            data=data
        )

