#!/bin/bash
# Production startup script for Railway

set -e

echo "🚀 Starting Tarragoneta in production mode..."

# Compile translations (migrations are handled by Procfile release phase)
echo "🌐 Compiling translations..."
python compile_translations.py 2>/dev/null || echo "⚠️  Translation compilation skipped"

echo "✅ Starting Gunicorn server..."

# Get port from environment or default to 5000
PORT=${PORT:-5000}

# Start Gunicorn
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    wsgi:app

