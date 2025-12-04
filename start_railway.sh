#!/bin/bash
# Railway startup script - runs both Celery worker and Gunicorn

set +e

echo "🚀 Starting Tarracograf on Railway..."

# Compile translations
echo "🌐 Compiling translations..."
python compile_translations.py
if [ $? -ne 0 ]; then
    echo "⚠️  Translation compilation failed, but continuing..."
fi

# Get port from environment
PORT=${PORT:-5000}

# Start Celery worker in background
echo "🔧 Starting Celery worker..."
celery -A celery_worker.celery worker --loglevel=info &
CELERY_PID=$!

# Wait a moment for Celery to start
sleep 2

# Start Gunicorn in foreground (this is the main process)
echo "✅ Starting Gunicorn server on port ${PORT}..."
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    wsgi:app

# If Gunicorn exits, kill Celery
kill $CELERY_PID 2>/dev/null

