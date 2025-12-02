"""
Celery tasks for sending emails
"""
from flask import current_app


def init_tasks(celery_app):
    """Initialize Celery tasks with the Celery app instance"""
    
    @celery_app.task(name='send_email_task', bind=True, max_retries=3)
    def send_email_task(self, to, subject, template, **kwargs):
        """
        Celery task to send an email asynchronously using EmailService
        
        Args:
            to: Email address or list of addresses
            subject: Email subject
            template: Template name (without .html)
            **kwargs: Additional context variables for the template
        """
        try:
            # Import here to avoid circular imports
            from app.services.email_service import EmailService
            
            # Temporarily disable Celery to avoid infinite recursion
            original_use_celery = current_app.config.get('USE_CELERY_FOR_EMAILS', True)
            current_app.config['USE_CELERY_FOR_EMAILS'] = False
            
            try:
                # Use EmailService to send email (synchronously since we're already in a task)
                # kwargs should already be JSON-serializable (only primitives)
                result = EmailService.send_email(to, subject, template, **kwargs)
                
                if result:
                    current_app.logger.info(f'Email sent successfully via Celery to {to}: {subject}')
                else:
                    current_app.logger.warning(f'Email sending failed via Celery to {to}: {subject}')
                
                return result
            finally:
                # Restore original setting
                current_app.config['USE_CELERY_FOR_EMAILS'] = original_use_celery
                
        except Exception as exc:
            current_app.logger.error(f'Error sending email via Celery to {to}: {str(exc)}', exc_info=True)
            # Retry with exponential backoff
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    
    # Return the task so it can be stored in app
    return send_email_task
