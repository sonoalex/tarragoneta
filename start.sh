#!/bin/bash
# Script para arrancar Tarragoneta

set -e

echo "🚀 Iniciando Tarragoneta..."
echo ""

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    echo "✓ Activando entorno virtual..."
    source .venv/bin/activate
fi

# Verificar que las dependencias estén instaladas
echo "✓ Verificando dependencias..."
python -c "import flask" 2>/dev/null || {
    echo "✗ Flask no encontrado. Instalando dependencias..."
    uv pip install --python .venv/bin/python -r requirements.txt || pip install -r requirements.txt
}

# Verificar que las migraciones existan
if [ ! -d "migrations" ]; then
    echo "⚠️  Migraciones no encontradas. Inicializando..."
    flask db init
    flask db migrate -m "Initial migration"
fi

# Aplicar migraciones
echo "✓ Aplicando migraciones..."
flask db upgrade || {
    echo "⚠️  Error aplicando migraciones. Intentando init-db..."
    flask init-db
}

# Compilar traducciones
echo "✓ Compilando traducciones..."
python compile_translations.py 2>/dev/null || echo "⚠️  No se pudieron compilar traducciones (puede estar bien)"

# Verificar usuario admin
echo "✓ Verificando usuario admin..."
python -c "
from app import create_app
from app.extensions import db
from app.models import User
app = create_app()
with app.app_context():
    admin = User.query.filter_by(email='admin@tarragoneta.org').first()
    if not admin:
        print('⚠️  Admin no encontrado. Ejecutando init-db...')
        import subprocess
        subprocess.run(['flask', 'init-db'])
    else:
        print('✓ Admin encontrado')
" || flask init-db

echo ""
echo "✅ Todo listo! Arrancando servidor..."
echo ""
echo "📝 Credenciales:"
echo "   Email: admin@tarragoneta.org"
echo "   Password: admin123"
echo ""
echo "🌐 Servidor en: http://127.0.0.1:5000"
echo ""

# Arrancar servidor
flask run --host=0.0.0.0 --port=5000 --debug

