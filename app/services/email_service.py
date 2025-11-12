"""
Email service for Tarragoneta
Handles all email sending with consistent styling
"""
from flask import render_template, current_app, url_for
from flask_mail import Message
from flask_babel import gettext as _
from app.extensions import mail
from datetime import datetime


class EmailService:
    """Service for sending emails with Tarragoneta branding"""
    
    @staticmethod
    def send_email(to, subject, template, **kwargs):
        """
        Send an email using a template
        
        Args:
            to: Email address or list of addresses
            subject: Email subject
            template: Template name (without .html)
            **kwargs: Additional context variables for the template
        """
        if current_app.config.get('MAIL_SUPPRESS_SEND', False):
            current_app.logger.info(f'[EMAIL SUPPRESSED] To: {to}, Subject: {subject}')
            return True
        
        try:
            # Add recipient_email to template context
            recipient_email = to if isinstance(to, str) else ', '.join(to)
            kwargs['recipient_email'] = recipient_email
            
            msg = Message(
                subject=subject,
                recipients=[to] if isinstance(to, str) else to,
                html=render_template(f'emails/{template}.html', **kwargs),
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'Tarragoneta <hola@tarragoneta.com>')
            )
            mail.send(msg)
            current_app.logger.info(f'Email sent successfully to {to}: {subject}')
            return True
        except Exception as e:
            current_app.logger.error(f'Error sending email to {to}: {str(e)}', exc_info=True)
            return False
    
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
            amount=donation.amount_euros
        )
    
    @staticmethod
    def send_initiative_approved(initiative, user):
        """Send email when initiative is approved"""
        return EmailService.send_email(
            to=user.email,
            subject=_('La teva iniciativa ha estat aprovada! ✅'),
            template='initiative_approved',
            initiative=initiative,
            user=user,
            initiative_url=url_for('initiatives.detail', id=initiative.id, _external=True)
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
        return EmailService.send_email(
            to=user.email,
            subject=_('Recordatori: La teva iniciativa és demà! 📅'),
            template='initiative_reminder',
            initiative=initiative,
            user=user,
            initiative_url=url_for('initiatives.detail', id=initiative.id, _external=True)
        )
    
    @staticmethod
    def send_participant_confirmation(initiative, participant_email, participant_name=None):
        """Send confirmation email to initiative participant"""
        return EmailService.send_email(
            to=participant_email,
            subject=_('Confirmació de participació en iniciativa'),
            template='participant_confirmation',
            initiative=initiative,
            participant_name=participant_name,
            initiative_url=url_for('initiatives.detail', id=initiative.id, _external=True)
        )
    
    @staticmethod
    def send_inventory_item_approved(item, reporter_email):
        """Send email when inventory item is approved"""
        return EmailService.send_email(
            to=reporter_email,
            subject=_('El teu reportatge ha estat aprovat! ✅'),
            template='inventory_approved',
            item=item,
            item_url=url_for('inventory.inventory_map', category=item.category, subcategory=item.subcategory, _external=True)
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

