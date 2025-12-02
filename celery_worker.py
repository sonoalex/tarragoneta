#!/usr/bin/env python
"""
Celery worker entry point
Run with: python celery_worker.py
Or: celery -A celery_worker.celery worker --loglevel=info
"""
from app import create_app

# Create Flask app
app = create_app()

# Get Celery app from Flask app
# Export at module level so 'celery -A celery_worker.celery' works
celery = app.celery

if __name__ == '__main__':
    # Run worker
    celery.worker_main(['worker', '--loglevel=info'])

