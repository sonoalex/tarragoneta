#!/usr/bin/env python
"""
Script completo para generar datos de seed para desarrollo local
Incluye iniciativas y datos de inventario
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.cli import create_sample_data
from app.extensions import db
from app.models import User, Role
from datetime import datetime, timezone

def create_test_users():
    """Create test users with different roles and statuses"""
    print("👥 Creating test users...")
    
    from app.extensions import user_datastore
    
    # Get roles
    admin_role = Role.query.filter_by(name='admin').first()
    user_role = Role.query.filter_by(name='user').first()
    moderator_role = Role.query.filter_by(name='moderator').first()
    
    if not admin_role or not user_role:
        print("⚠️  Roles not found. Please run 'flask init-db' first.")
        return
    
    # Test users data
    test_users = [
        {
            'email': 'user1@test.com',
            'username': 'user1',
            'password': 'test123',
            'active': True,
            'confirmed_at': datetime.now(timezone.utc),
            'roles': [user_role]
        },
        {
            'email': 'user2@test.com',
            'username': 'user2',
            'password': 'test123',
            'active': True,
            'confirmed_at': datetime.now(timezone.utc),
            'roles': [user_role]
        },
        {
            'email': 'user3@test.com',
            'username': 'user3',
            'password': 'test123',
            'active': False,  # Inactive user
            'confirmed_at': datetime.now(timezone.utc),
            'roles': [user_role]
        },
        {
            'email': 'user4@test.com',
            'username': 'user4',
            'password': 'test123',
            'active': True,
            'confirmed_at': None,  # Unconfirmed user
            'roles': [user_role]
        },
        {
            'email': 'moderator@test.com',
            'username': 'moderator',
            'password': 'test123',
            'active': True,
            'confirmed_at': datetime.now(timezone.utc),
            'roles': [moderator_role] if moderator_role else [user_role]
        },
        {
            'email': 'testuser@test.com',
            'username': 'testuser',
            'password': 'test123',
            'active': True,
            'confirmed_at': datetime.now(timezone.utc),
            'roles': [user_role]
        },
        {
            'email': 'juan@test.com',
            'username': 'juan',
            'password': 'test123',
            'active': True,
            'confirmed_at': datetime.now(timezone.utc),
            'roles': [user_role]
        },
        {
            'email': 'maria@test.com',
            'username': 'maria',
            'password': 'test123',
            'active': True,
            'confirmed_at': datetime.now(timezone.utc),
            'roles': [user_role]
        },
    ]
    
    created = 0
    for user_data in test_users:
        # Check if user already exists
        existing = User.query.filter_by(email=user_data['email']).first()
        if existing:
            continue
        
        # Create user
        roles = user_data.pop('roles')
        user = user_datastore.create_user(**user_data)
        for role in roles:
            user_datastore.add_role_to_user(user, role)
        created += 1
    
    db.session.commit()
    print(f"✅ Created {created} test users")
    print("   Test users credentials:")
    print("   - user1@test.com / test123 (active, confirmed)")
    print("   - user2@test.com / test123 (active, confirmed)")
    print("   - user3@test.com / test123 (inactive, confirmed)")
    print("   - user4@test.com / test123 (active, unconfirmed)")
    print("   - moderator@test.com / test123 (moderator)")
    print("   - testuser@test.com / test123 (active, confirmed)")
    print("   - juan@test.com / test123 (active, confirmed)")
    print("   - maria@test.com / test123 (active, confirmed)")

def seed_all():
    """Generate all seed data"""
    app = create_app()
    
    with app.app_context():
        print("🌱 Generating seed data for local development...")
        print("")
        
        # Create test users
        try:
            create_test_users()
        except Exception as e:
            print(f"⚠️  Error creating test users: {e}")
        
        print("")
        
        # Create sample initiatives
        print("📋 Creating sample initiatives...")
        try:
            create_sample_data()
        except Exception as e:
            print(f"⚠️  Error creating initiatives: {e}")
        
        print("")
        
        # Create inventory seed data
        print("🗑️  Creating inventory seed data...")
        try:
            from seed_data import generate_seed_data
            generate_seed_data(num_items=50)
        except Exception as e:
            print(f"⚠️  Error creating inventory data: {e}")
        
        print("")
        print("✅ Seed data generation complete!")
        print("")
        print("You can now:")
        print("  - View initiatives at: http://127.0.0.1:5000/")
        print("  - View inventory map at: http://127.0.0.1:5000/inventory/map")
        print("  - Admin dashboard: http://127.0.0.1:5000/admin/dashboard")
        print("  - User management: http://127.0.0.1:5000/admin/users")
        print("  - Admin login: admin@tarragoneta.org / admin123 (desarrollo - cambiar en producción)")
        print("  - Test users: user1@test.com / test123, etc.")

if __name__ == '__main__':
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Generate seed data for local development')
    parser.add_argument('--initiatives-only', action='store_true', help='Only create initiatives')
    parser.add_argument('--inventory-only', action='store_true', help='Only create inventory data')
    parser.add_argument('--users-only', action='store_true', help='Only create test users')
    parser.add_argument('--inventory-count', type=int, default=50, help='Number of inventory items (default: 50)')
    parser.add_argument('--clear-inventory', action='store_true', help='Clear existing inventory items before creating new ones')
    parser.add_argument('--reset-db', action='store_true', help='Delete SQLite database and recreate everything')
    
    args = parser.parse_args()
    
    app = create_app()
    with app.app_context():
        # Reset database if requested
        if args.reset_db:
            print("🗑️  Resetting database...")
            db_file = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
            if db_file and os.path.exists(db_file):
                os.remove(db_file)
                print(f"✅ Deleted {db_file}")
            
            # Reinitialize database
            print("📦 Reinitializing database...")
            from app.cli import init_db_command
            init_db_command()
            print("✅ Database reinitialized")
            print("")
        
        if args.users_only:
            print("👥 Creating test users only...")
            create_test_users()
        elif args.initiatives_only:
            print("📋 Creating sample initiatives only...")
            create_sample_data()
        elif args.inventory_only:
            print("🗑️  Creating inventory seed data only...")
            from seed_data import generate_seed_data
            if args.clear_inventory:
                from app.models import InventoryItem
                print("🗑️  Clearing existing inventory items...")
                InventoryItem.query.delete()
                db.session.commit()
                print("✅ Cleared existing items")
            generate_seed_data(num_items=args.inventory_count)
        else:
            seed_all()

