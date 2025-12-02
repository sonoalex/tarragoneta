"""
Celery tasks for Tarracograf
"""
from app.tasks.email_tasks import init_tasks

__all__ = ['init_tasks']

