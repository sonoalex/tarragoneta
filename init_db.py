#!/usr/bin/env python
"""
Database initialization script for Railway/production
This script ensures the database is properly set up before the app starts
"""
import os
from datetime import datetime
from app import create_app
from app.extensions import db
from app.models import Role, User

# Silenciar logging verboso cuando se ejecuta desde scripts
os.environ['FLASK_SILENT_STARTUP'] = '1'

# Detectar entorno
if 'FLASK_ENV' not in os.environ:
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        os.environ['FLASK_ENV'] = 'production'
    else:
        os.environ['FLASK_ENV'] = 'development'

def init_database():
    """Initialize database with tables and default data"""
    app = create_app()
    
    with app.app_context():
        print("🔧 Inicializando base de datos...")
        
        # Aplicar migraciones primero
        try:
            from flask_migrate import upgrade
            print("📦 Aplicando migraciones...")
            upgrade()
            print("✓ Migraciones aplicadas")
        except Exception as e:
            # Si no hay migraciones o fallan, crear tablas directamente
            print("📦 Creando tablas...")
            db.create_all()
            print("✓ Tablas creadas")
        
        # Crear roles si no existen
        if not Role.query.first():
            print("👥 Creando roles...")
            admin_role = Role(name='admin', description='Administrator')
            user_role = Role(name='user', description='Regular User')
            moderator_role = Role(name='moderator', description='Moderator')
            db.session.add_all([admin_role, user_role, moderator_role])
            db.session.commit()
            print("✓ Roles creados")
        
        # Crear usuario admin si no existe
        admin_user = User.query.filter_by(email='admin@tarragoneta.org').first()
        if not admin_user:
            print("👤 Creando usuario admin...")
            from app.extensions import user_datastore
            admin_role = Role.query.filter_by(name='admin').first()
            
            admin_user = user_datastore.create_user(
                email='admin@tarragoneta.org',
                username='admin',
                password='admin123',
                active=True,
                confirmed_at=datetime.now(),
                roles=[admin_role]
            )
            db.session.commit()
            print("✓ Usuario admin creado")
        
        print("✅ Base de datos inicializada!")

if __name__ == '__main__':
    init_database()

