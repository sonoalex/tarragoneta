#!/bin/bash
# Railway worker startup script for Celery

set +e

echo "🔧 Starting Celery worker on Railway..."

# Check Redis connection
echo "🔍 Checking Redis connection..."
if [ -n "$REDIS_URL" ]; then
    echo "✅ REDIS_URL is set: ${REDIS_URL:0:20}..."
else
    echo "⚠️  REDIS_URL not set, checking CELERY_BROKER_URL..."
    if [ -n "$CELERY_BROKER_URL" ]; then
        echo "✅ CELERY_BROKER_URL is set: ${CELERY_BROKER_URL:0:20}..."
    else
        echo "❌ ERROR: Neither REDIS_URL nor CELERY_BROKER_URL is set!"
        echo "   Worker cannot start without Redis connection."
        exit 1
    fi
fi

# Check if we can import the app
echo "🔍 Checking Flask app..."
python -c "from app import create_app; app = create_app(); print('✅ Flask app created successfully')" || {
    echo "❌ ERROR: Cannot create Flask app"
    exit 1
}

# Start Celery worker
echo "✅ Starting Celery worker..."
exec celery -A celery_worker.celery worker --loglevel=info --concurrency=2

