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

def seed_all():
    """Generate all seed data"""
    app = create_app()
    
    with app.app_context():
        print("🌱 Generating seed data for local development...")
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
        print("  - Login: admin@tarragoneta.org / admin123")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate seed data for local development')
    parser.add_argument('--initiatives-only', action='store_true', help='Only create initiatives')
    parser.add_argument('--inventory-only', action='store_true', help='Only create inventory data')
    parser.add_argument('--inventory-count', type=int, default=50, help='Number of inventory items (default: 50)')
    parser.add_argument('--clear-inventory', action='store_true', help='Clear existing inventory items before creating new ones')
    
    args = parser.parse_args()
    
    app = create_app()
    with app.app_context():
        if args.initiatives_only:
            print("📋 Creating sample initiatives only...")
            create_sample_data()
        elif args.inventory_only:
            print("🗑️  Creating inventory seed data only...")
            from seed_data import generate_seed_data
            if args.clear_inventory:
                from app.models import InventoryItem
                from app.extensions import db
                print("🗑️  Clearing existing inventory items...")
                InventoryItem.query.delete()
                db.session.commit()
                print("✅ Cleared existing items")
            generate_seed_data(num_items=args.inventory_count)
        else:
            seed_all()

