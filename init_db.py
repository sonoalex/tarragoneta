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
            print(f"⚠️  Error aplicando migraciones: {str(e)}")
            # Si no hay migraciones o fallan, crear tablas directamente
            print("📦 Creando tablas...")
            db.create_all()
            print("✓ Tablas creadas")
        
        # Verificar y añadir columnas faltantes manualmente (fallback)
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('inventory_item')]
            
            # Verificar si falta resolved_count
            if 'resolved_count' not in columns:
                print("🔧 Añadiendo columna resolved_count a inventory_item...")
                if db.engine.dialect.name == 'postgresql':
                    db.session.execute(text('ALTER TABLE inventory_item ADD COLUMN IF NOT EXISTS resolved_count INTEGER DEFAULT 0'))
                else:
                    db.session.execute(text('ALTER TABLE inventory_item ADD COLUMN resolved_count INTEGER DEFAULT 0'))
                db.session.commit()
                print("✓ Columna resolved_count añadida")
        except Exception as e:
            print(f"⚠️  Error verificando/añadiendo columnas: {str(e)}")
            db.session.rollback()
        
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
        admin_email = app.config.get('ADMIN_USER_EMAIL', 'hola@tarracograf.cat')
        admin_password = app.config.get('ADMIN_PASSWORD')
        
        # Verificar si el usuario admin ya existe (por email o username)
        admin_user = User.query.filter_by(email=admin_email).first()
        admin_user_by_username = User.query.filter_by(username='admin').first()
        
        if admin_user:
            print(f"✓ Usuario admin ya existe (email: {admin_email})")
        elif admin_user_by_username:
            print(f"✓ Usuario admin ya existe (username: admin)")
        else:
            # Usuario no existe, crearlo
            if not admin_password:
                # Solo en desarrollo: usar password por defecto si no está configurado
                if app.config.get('ENV') == 'development' or app.config.get('FLASK_ENV') == 'development':
                    admin_password = 'admin123'  # Solo para desarrollo local
                    print("👤 Creando usuario admin (desarrollo)...")
                    print("⚠️  Usando contraseña por defecto. Cambia la contraseña después del primer login!")
                else:
                    print("⚠️  ADMIN_PASSWORD no configurado. No se creará usuario admin.")
                    print("   Configura ADMIN_PASSWORD en variables de entorno para producción.")
                    return
            
            print("👤 Creando usuario admin...")
            from app.extensions import user_datastore
            admin_role = Role.query.filter_by(name='admin').first()
            
            try:
                admin_user = user_datastore.create_user(
                    email=admin_email,
                    username='admin',
                    password=admin_password,
                    active=True,
                    confirmed_at=datetime.now(),
                    roles=[admin_role]
                )
                db.session.commit()
                print("✓ Usuario admin creado")
                if app.config.get('ENV') == 'development' or app.config.get('FLASK_ENV') == 'development':
                    print(f"   Email: {admin_email}")
                    print(f"   Password: {admin_password}")
            except Exception as e:
                db.session.rollback()
                # Si falla por constraint, el usuario probablemente ya existe
                if 'UNIQUE constraint' in str(e) or 'IntegrityError' in str(type(e).__name__):
                    print(f"⚠️  Usuario admin ya existe (error de constraint: {str(e)})")
                    print(f"   Email: {admin_email}")
                else:
                    print(f"⚠️  Error creando usuario admin: {str(e)}")
                    raise
        
        print("✅ Base de datos inicializada!")

if __name__ == '__main__':
    init_database()

