#!/bin/bash
# Production worker startup script for Railway
# This script is used when Railway.json is configured

echo "🚀 Starting RQ worker for email queue (production)..."

# Compile translations (if needed)
echo "🌐 Compiling translations..."
python compile_translations.py 2>/dev/null || echo "⚠️  Translation compilation skipped"

# Start worker
echo "✅ Starting worker..."
python worker.py

