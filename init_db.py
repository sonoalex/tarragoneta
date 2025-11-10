#!/usr/bin/env python
"""
Database initialization script for Railway/production
This script ensures the database is properly set up before the app starts
"""
import os
import sys

# Set production environment
os.environ['FLASK_ENV'] = 'production'

from app import create_app
from app.extensions import db
from app.models import Role, User
from flask_security import hash_password
from datetime import datetime

def init_database():
    """Initialize database with tables and default data"""
    app = create_app('production')
    
    with app.app_context():
        print("🔧 Initializing database...")
        
        # Try migrations first (preferred method)
        tables_created = False
        try:
            from flask_migrate import upgrade
            print("📦 Applying database migrations...")
            upgrade()
            print("✓ Migrations applied successfully")
            tables_created = True
        except Exception as e:
            print(f"⚠️  Migrations failed: {e}")
            print("   This might be normal if migrations don't exist yet")
        
        # Fallback to db.create_all() if migrations didn't work
        if not tables_created:
            try:
                print("📦 Creating database tables using db.create_all()...")
                db.create_all()
                print("✓ Tables created successfully")
                tables_created = True
            except Exception as e:
                print(f"✗ Error creating tables: {e}")
                # Check if tables already exist
                try:
                    from app.models import Initiative
                    # Try a simple query to see if tables exist
                    Initiative.query.limit(1).all()
                    print("✓ Tables already exist")
                    tables_created = True
                except Exception as e2:
                    print(f"✗ Tables don't exist and couldn't be created: {e2}")
                    sys.exit(1)
        
        # Ensure subcategory column exists (for existing databases)
        try:
            from app.models import InventoryItem
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('inventory_item')]
            
            if 'subcategory' not in columns:
                print("📦 Adding subcategory column to inventory_item...")
                import sqlalchemy as sa
                with db.engine.connect() as conn:
                    # Add column
                    conn.execute(sa.text("ALTER TABLE inventory_item ADD COLUMN subcategory VARCHAR(50)"))
                    conn.commit()
                
                # Migrate existing data
                print("📦 Migrating existing category data to subcategory...")
                with db.engine.connect() as conn:
                    # Map old categories to new structure
                    conn.execute(sa.text("""
                        UPDATE inventory_item 
                        SET subcategory = category,
                            category = 'palomas'
                        WHERE category IN ('excremento', 'nido', 'paloma', 'plumas')
                    """))
                    conn.execute(sa.text("""
                        UPDATE inventory_item 
                        SET subcategory = category,
                            category = 'basura'
                        WHERE category IN ('basura_desborda', 'vertidos')
                    """))
                    conn.execute(sa.text("""
                        UPDATE inventory_item 
                        SET subcategory = COALESCE(subcategory, 'otro'),
                            category = 'palomas'
                        WHERE subcategory IS NULL
                    """))
                    conn.commit()
                
                # Make NOT NULL if PostgreSQL
                if db.engine.dialect.name == 'postgresql':
                    with db.engine.connect() as conn:
                        conn.execute(sa.text("ALTER TABLE inventory_item ALTER COLUMN subcategory SET NOT NULL"))
                        conn.commit()
                
                print("✓ Subcategory column added and data migrated")
        except Exception as e:
            print(f"⚠️  Could not add subcategory column: {e}")
            print("   This might be normal if column already exists or migration handled it")
        
        # Create roles
        if not Role.query.first():
            print("👥 Creating default roles...")
            admin_role = Role(name='admin', description='Administrator')
            user_role = Role(name='user', description='Regular User')
            moderator_role = Role(name='moderator', description='Moderator')
            
            db.session.add_all([admin_role, user_role, moderator_role])
            db.session.commit()
            print("✓ Roles created")
        
        # Create admin user
        admin_user = User.query.filter_by(email='admin@tarragoneta.org').first()
        if not admin_user:
            print("👤 Creating admin user...")
            from app.extensions import user_datastore
            admin_role = Role.query.filter_by(name='admin').first()
            
            if admin_role:
                # Flask-Security-Too's create_user hashes the password automatically
                admin_user = user_datastore.create_user(
                    email='admin@tarragoneta.org',
                    username='admin',
                    password='admin123',  # Flask-Security hashes this automatically
                    active=True,
                    confirmed_at=datetime.now(),
                    roles=[admin_role]
                )
                db.session.commit()
                print("✓ Admin user created")
                print("  Email: admin@tarragoneta.org")
                print("  Password: admin123")
            else:
                print("✗ Admin role not found")
        else:
            print("✓ Admin user already exists")
        
        print("✅ Database initialization complete!")

if __name__ == '__main__':
    init_database()

