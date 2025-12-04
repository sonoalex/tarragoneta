#!/bin/bash
# Railway worker startup script for Celery

set +e

echo "🔧 Starting Celery worker on Railway..."

# Start Celery worker
exec celery -A celery_worker.celery worker --loglevel=info

