#!/bin/bash
# Script para arrancar el worker de RQ localmente

echo "🚀 Iniciando worker de RQ para cola de emails..."
echo ""

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    echo "✓ Activando entorno virtual..."
    source .venv/bin/activate
fi

# Configurar Flask
export FLASK_APP=app.py
export FLASK_ENV=development

# Verificar que Redis esté corriendo
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis no está corriendo!"
    echo ""
    echo "Para iniciar Redis:"
    echo "  macOS: brew services start redis"
    echo "  Docker: docker run -d -p 6379:6379 redis:latest"
    echo ""
    exit 1
fi

echo "✓ Redis está corriendo"
echo ""

# Arrancar worker
python worker.py

