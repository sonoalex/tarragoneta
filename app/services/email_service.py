"""
Email service for Tarracograf
Handles all email sending with consistent styling
Uses provider pattern for flexible email delivery (SMTP, Console)
Uses Celery for asynchronous email sending when available
"""
import os
from flask import render_template, current_app, url_for
from flask_babel import gettext as _
from app.container import provide
from app.providers.base import EmailProvider
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.providers.base import EmailProvider


class EmailService:
    """Service for sending emails with Tarracograf branding"""
    
    @staticmethod
    def _is_staging():
        """Check if we're in staging environment"""
        # Check Railway environment variable
        railway_env = os.environ.get('RAILWAY_ENVIRONMENT', '').lower()
        if railway_env == 'staging':
            return True
        
        # Check Railway service name (often contains 'staging')
        railway_service = os.environ.get('RAILWAY_SERVICE_NAME', '').lower()
        if 'staging' in railway_service:
            return True
        
        # Check FLASK_ENV
        flask_env = os.environ.get('FLASK_ENV', '').lower()
        if flask_env == 'staging':
            return True
        
        # Check app config ENV
        try:
            app_env = current_app.config.get('ENV', 'development').lower()
            if app_env == 'staging':
                return True
        except:
            pass
        
        return False
    
    @staticmethod
    def _add_staging_prefix(subject):
        """Add staging prefix to email subject if in staging"""
        if EmailService._is_staging():
            return f"[STAGING] {subject}"
        return subject
    
    @staticmethod
    def _send_email_direct(to, subject, template, **kwargs):
        """
        Send an email directly using the provider (without Celery).
        Used when Celery is disabled or when called from within a Celery task.
        """
        # Render the email template
        # Flask can generate external URLs without request context if SERVER_NAME is configured
        # If not configured, we'll create a minimal request context
        try:
            # Check if SERVER_NAME is configured (standard Flask way)
            if current_app.config.get('SERVER_NAME'):
                # Flask can generate external URLs directly
                html = render_template(f'emails/{template}.html', **kwargs)
            else:
                # Fallback: create a minimal request context
                # Extract domain from BASE_URL if available, otherwise use default
                base_url = os.environ.get('BASE_URL') or current_app.config.get('BASE_URL')
                if base_url:
                    # Parse BASE_URL to get scheme and host
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url)
                    with current_app.test_request_context(
                        base_url=base_url,
                        environ_base={'SERVER_NAME': parsed.netloc or 'localhost:5000'}
                    ):
                        html = render_template(f'emails/{template}.html', **kwargs)
                else:
                    # Last resort: use test_request_context with defaults
                    with current_app.test_request_context():
                        html = render_template(f'emails/{template}.html', **kwargs)
        except Exception as e:
            current_app.logger.error(f'Error rendering email template {template}: {str(e)}', exc_info=True)
            return False
        
        # Get the email provider from DI container
        try:
            provider = provide('email_provider')
            if not provider:
                current_app.logger.error('Email provider not available')
                return False
            
            # Add staging prefix to subject if in staging
            final_subject = EmailService._add_staging_prefix(subject)
            
            # Add staging indicator to email context
            kwargs['is_staging'] = EmailService._is_staging()
            
            # Send email via provider
            result = provider.send_email(to, final_subject, html)
            return result
        except Exception as e:
            current_app.logger.error(f'Error sending email to {to}: {str(e)}', exc_info=True)
            return False
    
    @staticmethod
    def send_email(to, subject, template, **kwargs):
        """
        Send an email using a template (asynchronously via Celery if enabled)
        
        Args:
            to: Email address or list of addresses
            subject: Email subject
            template: Template name (without .html)
            **kwargs: Additional context variables for the template
        """
        # Add staging indicator to kwargs
        kwargs['is_staging'] = EmailService._is_staging()
        
        # Check if Celery should be used
        use_celery = current_app.config.get('USE_CELERY_FOR_EMAILS', True)
        
        if not use_celery:
            # Send directly without Celery
            return EmailService._send_email_direct(to, subject, template, **kwargs)
        
        # Get Celery task from app (use getattr instead of .get() to avoid Flask setup restrictions)
        send_email_task = getattr(current_app, 'send_email_task', None)
        if not send_email_task:
            current_app.logger.warning('Celery task not available, falling back to direct send')
            return EmailService._send_email_direct(to, subject, template, **kwargs)
        
        # Enqueue email task (kwargs should already be JSON-serializable)
        # Note: staging prefix will be added in _send_email_direct
        task = send_email_task.delay(to, subject, template, **kwargs)
        current_app.logger.info(f'Email task enqueued to {to}: {subject} (task_id: {task.id})')
        return True
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email after registration with confirmation link"""
        try:
            login_url = url_for('security.login', _external=True)
        except:
            login_url = None
        
        # Generate confirmation token if user is not confirmed
        confirmation_url = None
        if not user.confirmed_at:
            try:
                from itsdangerous import URLSafeTimedSerializer
                serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
                token = serializer.dumps(user.email, salt=current_app.config.get('SECURITY_PASSWORD_SALT', 'tarracograf-salt-2024'))
                confirmation_url = url_for('main.confirm_email', token=token, _external=True)
            except Exception as e:
                current_app.logger.error(f'Error generating confirmation token: {str(e)}', exc_info=True)
        
        return EmailService.send_email(
            to=user.email,
            subject=_('Benvingut/da a Tarracograf! 🌱'),
            template='welcome',
            username=user.username or user.email,
            user_email=user.email,
            login_url=login_url,
            confirmation_url=confirmation_url
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
            username=user.username if user else None,
            user_email=user.email if user else None,
            amount=donation.amount_euros if hasattr(donation, 'amount_euros') else None,
            donation_date=donation.completed_at.strftime('%d/%m/%Y %H:%M') if hasattr(donation, 'completed_at') and donation.completed_at else None
        )
    
    @staticmethod
    def send_initiative_approved(initiative, user):
        """Send email when initiative is approved"""
        try:
            initiative_url = url_for('initiatives.detail', id=initiative.id, _external=True)
        except Exception:
            initiative_url = None
        return EmailService.send_email(
            to=user.email,
            subject=_('La teva iniciativa ha estat aprovada! ✅'),
            template='initiative_approved',
            username=user.username or user.email,
            user_email=user.email,
            initiative_title=initiative.title,
            initiative_date=initiative.date.strftime('%d/%m/%Y') if initiative.date else None,
            initiative_location=initiative.location,
            initiative_url=initiative_url
        )
    
    @staticmethod
    def send_initiative_rejected(initiative, user, reason=None):
        """Send email when initiative is rejected"""
        return EmailService.send_email(
            to=user.email,
            subject=_('Informació sobre la teva iniciativa'),
            template='initiative_rejected',
            username=user.username or user.email,
            user_email=user.email,
            initiative_title=initiative.title,
            reason=reason
        )
    
    @staticmethod
    def send_initiative_reminder(initiative, user):
        """Send reminder email before initiative date"""
        try:
            initiative_url = url_for('initiatives.detail', id=initiative.id, _external=True)
        except Exception:
            initiative_url = None
        return EmailService.send_email(
            to=user.email,
            subject=_('Recordatori: La teva iniciativa és demà! 📅'),
            template='initiative_reminder',
            username=user.username or user.email,
            user_email=user.email,
            initiative_title=initiative.title,
            initiative_date=initiative.date.strftime('%d/%m/%Y') if initiative.date else None,
            initiative_time=str(initiative.time) if hasattr(initiative, 'time') and initiative.time else None,
            initiative_location=initiative.location,
            initiative_url=initiative_url
        )
    
    @staticmethod
    def send_participant_confirmation(initiative, participant_email, participant_name=None):
        """Send confirmation email to initiative participant"""
        try:
            initiative_url = url_for('initiatives.detail', id=initiative.id, _external=True)
        except Exception:
            initiative_url = None
        return EmailService.send_email(
            to=participant_email,
            subject=_('Confirmació de participació en iniciativa'),
            template='participant_confirmation',
            initiative_title=initiative.title,
            initiative_date=initiative.date.strftime('%d/%m/%Y') if initiative.date else None,
            initiative_time=str(initiative.time) if hasattr(initiative, 'time') and initiative.time else None,
            initiative_location=initiative.location,
            participant_name=participant_name,
            initiative_url=initiative_url
        )
    
    @staticmethod
    def send_inventory_item_approved(item, reporter_email):
        """Send email when inventory item is approved"""
        try:
            item_url = url_for('inventory.inventory_map', category=item.category, subcategory=item.subcategory, _external=True)
        except Exception:
            item_url = None
        
        # Get full category name for display
        from app.utils import get_inventory_category_name, get_inventory_subcategory_name
        category_name = get_inventory_category_name(item.category)
        subcategory_name = get_inventory_subcategory_name(item.subcategory) if item.subcategory else None
        full_category = f"{category_name}" + (f" - {subcategory_name}" if subcategory_name else "")
        
        return EmailService.send_email(
            to=reporter_email,
            subject=_('El teu reportatge ha estat aprovat! ✅'),
            template='inventory_approved',
            item_category=item.category,
            item_subcategory=item.subcategory,
            item_full_category=full_category,
            item_address=item.address,
            item_description=item.description,
            item_url=item_url
        )
    
    @staticmethod
    def send_inventory_item_rejected(item, reporter_email, reason=None):
        """Send email when inventory item is rejected"""
        return EmailService.send_email(
            to=reporter_email,
            subject=_('Informació sobre el teu reportatge'),
            template='inventory_rejected',
            item_category=item.category,
            item_subcategory=item.subcategory,
            item_description=item.description,
            reason=reason
        )
    
    @staticmethod
    def send_contact_form_response(contact_email, subject, message):
        """Send response to contact form submission"""
        return EmailService.send_email(
            to=contact_email,
            subject=_('Gràcies per contactar amb Tarracograf'),
            template='contact_response',
            contact_email=contact_email,
            contact_subject=subject,  # Renamed to avoid conflict with email subject
            message=message
        )
    
    @staticmethod
    def send_admin_notification(admin_email, notification_type, data):
        """Send notification to admin"""
        # Create a more descriptive subject based on notification type
        subject = f"Tarracograf - {notification_type}"
        if data.get('subject'):
            subject = f"Tarracograf - {notification_type}: {data.get('subject')}"
        
        current_app.logger.info(f'Sending admin notification: {notification_type} to {admin_email}')
        result = EmailService.send_email(
            to=admin_email,
            subject=subject,
            template='admin_notification',
            notification_type=notification_type,
            data=data
        )
        if result:
            current_app.logger.info(f'Admin notification sent successfully to {admin_email}')
        else:
            current_app.logger.warning(f'Admin notification failed to send to {admin_email}')
        return result
    
    @staticmethod
    def send_password_reset_email(user, reset_link):
        """Send password reset email"""
        return EmailService.send_email(
            to=user.email,
            subject=_('Restablecer tu contraseña en Tarracograf'),
            template='password_reset',
            username=user.username or user.email,
            user_email=user.email,
            reset_link=reset_link,
            recipient_email=user.email
        )

