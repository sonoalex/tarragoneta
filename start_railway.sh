#!/bin/bash
# Railway web service startup script (Gunicorn only)

set +e

echo "🚀 Starting Tarracograf web service on Railway..."

# Compile translations
echo "🌐 Compiling translations..."
python compile_translations.py
if [ $? -ne 0 ]; then
    echo "⚠️  Translation compilation failed, but continuing..."
fi

# Get port from environment
PORT=${PORT:-5000}

# Start Gunicorn (this is the main process for web service)
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

