#!/bin/bash
# Script para arrancar Tarragoneta

echo "🚀 Iniciando Tarragoneta..."
echo ""

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    echo "✓ Activando entorno virtual..."
    source .venv/bin/activate
fi

# Configurar Flask
export FLASK_APP=app.py
export FLASK_ENV=development

# Inicializar base de datos (crea tablas, aplica migraciones, crea datos iniciales)
echo "✓ Inicializando base de datos..."
uv run python init_db.py

# Compilar traducciones
echo "✓ Compilando traducciones..."
uv run python compile_translations.py 2>/dev/null || echo "⚠️  No se pudieron compilar traducciones (continuando...)"

echo ""
echo "✅ Todo listo! Arrancando servidor..."
echo ""
echo "📝 Credenciales (desarrollo):"
echo "   Email: admin@tarragoneta.org"
echo "   Password: admin123 (cambiar después del primer login)"
echo ""
echo "🌐 Servidor en: http://127.0.0.1:5000"
echo ""

# Arrancar servidor
uv run flask run --host=0.0.0.0 --port=5000 --debug
