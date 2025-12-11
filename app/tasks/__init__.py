"""
Celery tasks for Tarracograf
"""
from app.tasks.email_tasks import init_tasks
from app.tasks.image_tasks import init_image_tasks

__all__ = ['init_tasks', 'init_image_tasks']

