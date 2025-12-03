#!/usr/bin/env python
"""
Script para generar datos de ejemplo del inventario (palomas, basura, etc.) en Tarragona.

Este script:
- Genera items de inventario con coordenadas reales de Tarragona
- Asigna automáticamente la sección administrativa basándose en las coordenadas
- Crea imágenes de ejemplo (opcional)
- Distribuye items por categorías y estados de forma realista

Uso:
    python seed_data.py --count 50 --clear
"""
import os
import sys
from datetime import datetime, timedelta, timezone
import random
import urllib.request
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import InventoryItem, User, Section
from app.extensions import db
from app.config import Config

# Coordenadas reales de lugares conocidos en Tarragona
TARRAGONA_LOCATIONS = [
    # Centro histórico
    {'name': 'Rambla Nova', 'lat': 41.1189, 'lng': 1.2586, 'address': 'Rambla Nova, Tarragona'},
    {'name': 'Plaça de la Font', 'lat': 41.1195, 'lng': 1.2580, 'address': 'Plaça de la Font, Tarragona'},
    {'name': 'Catedral de Tarragona', 'lat': 41.1190, 'lng': 1.2575, 'address': 'Catedral de Tarragona'},
    {'name': 'Passeig Arqueològic', 'lat': 41.1200, 'lng': 1.2570, 'address': 'Passeig Arqueològic, Tarragona'},
    {'name': 'Plaça del Rei', 'lat': 41.1185, 'lng': 1.2585, 'address': 'Plaça del Rei, Tarragona'},
    
    # Playas y zona costera
    {'name': 'Playa del Miracle', 'lat': 41.1100, 'lng': 1.2500, 'address': 'Playa del Miracle, Tarragona'},
    {'name': 'Playa Llarga', 'lat': 41.1050, 'lng': 1.2450, 'address': 'Playa Llarga, Tarragona'},
    {'name': 'Balcó del Mediterrani', 'lat': 41.1150, 'lng': 1.2550, 'address': 'Balcó del Mediterrani, Tarragona'},
    {'name': 'Port de Tarragona', 'lat': 41.1080, 'lng': 1.2480, 'address': 'Port de Tarragona'},
    
    # Zonas residenciales
    {'name': 'Torreforta', 'lat': 41.1250, 'lng': 1.2650, 'address': 'Torreforta, Tarragona'},
    {'name': 'Bonavista', 'lat': 41.1300, 'lng': 1.2700, 'address': 'Bonavista, Tarragona'},
    {'name': 'Sant Pere i Sant Pau', 'lat': 41.1220, 'lng': 1.2600, 'address': 'Sant Pere i Sant Pau, Tarragona'},
    
    # Parques y zonas verdes
    {'name': 'Parc de la Ciutat', 'lat': 41.1280, 'lng': 1.2620, 'address': 'Parc de la Ciutat, Tarragona'},
    {'name': 'Parc del Francolí', 'lat': 41.1150, 'lng': 1.2400, 'address': 'Parc del Francolí, Tarragona'},
    {'name': 'Jardins de la Rambla', 'lat': 41.1180, 'lng': 1.2580, 'address': 'Jardins de la Rambla Nova'},
    
    # Edificios y monumentos
    {'name': 'Amfiteatre Romà', 'lat': 41.1140, 'lng': 1.2560, 'address': 'Amfiteatre Romà, Tarragona'},
    {'name': 'Circ Romà', 'lat': 41.1200, 'lng': 1.2590, 'address': 'Circ Romà, Tarragona'},
    {'name': 'Prat de la Riba', 'lat': 41.1210, 'lng': 1.2610, 'address': 'Avinguda Prat de la Riba, Tarragona'},
    {'name': 'Estació de Tarragona', 'lat': 41.1230, 'lng': 1.2630, 'address': 'Estació de Tarragona'},
    
    # Zonas comerciales
    {'name': 'Centro Comercial Parc Central', 'lat': 41.1270, 'lng': 1.2680, 'address': 'Parc Central, Tarragona'},
    {'name': 'Mercat Central', 'lat': 41.1195, 'lng': 1.2590, 'address': 'Mercat Central, Tarragona'},
    
    # Más ubicaciones
    {'name': 'Carrer Major', 'lat': 41.1188, 'lng': 1.2582, 'address': 'Carrer Major, Tarragona'},
    {'name': 'Plaça dels Sedassos', 'lat': 41.1192, 'lng': 1.2578, 'address': 'Plaça dels Sedassos, Tarragona'},
    {'name': 'Plaça de la Imperial Tarraco', 'lat': 41.1175, 'lng': 1.2588, 'address': 'Plaça de la Imperial Tarraco'},
    {'name': 'Carrer de la Unió', 'lat': 41.1190, 'lng': 1.2585, 'address': 'Carrer de la Unió, Tarragona'},
    {'name': 'Avinguda Catalunya', 'lat': 41.1240, 'lng': 1.2640, 'address': 'Avinguda Catalunya, Tarragona'},
    {'name': 'Carrer de Sant Pau', 'lat': 41.1205, 'lng': 1.2595, 'address': 'Carrer de Sant Pau, Tarragona'},
    {'name': 'Plaça de la Generalitat', 'lat': 41.1183, 'lng': 1.2583, 'address': 'Plaça de la Generalitat'},
    {'name': 'Carrer de les Coques', 'lat': 41.1193, 'lng': 1.2577, 'address': 'Carrer de les Coques, Tarragona'},
    {'name': 'Plaça del Fòrum', 'lat': 41.1187, 'lng': 1.2587, 'address': 'Plaça del Fòrum, Tarragona'},
    {'name': 'Carrer de la Merceria', 'lat': 41.1191, 'lng': 1.2581, 'address': 'Carrer de la Merceria, Tarragona'},
    {'name': 'Plaça de les Cols', 'lat': 41.1186, 'lng': 1.2584, 'address': 'Plaça de les Cols, Tarragona'},
    {'name': 'Carrer de la Nau', 'lat': 41.1189, 'lng': 1.2579, 'address': 'Carrer de la Nau, Tarragona'},
    {'name': 'Plaça del Pallol', 'lat': 41.1184, 'lng': 1.2586, 'address': 'Plaça del Pallol, Tarragona'},
    {'name': 'Carrer de Sant Llorenç', 'lat': 41.1194, 'lng': 1.2576, 'address': 'Carrer de Sant Llorenç, Tarragona'},
    {'name': 'Plaça de la Seu', 'lat': 41.1182, 'lng': 1.2584, 'address': 'Plaça de la Seu, Tarragona'},
    {'name': 'Carrer de les Escales Velles', 'lat': 41.1185, 'lng': 1.2581, 'address': 'Carrer de les Escales Velles'},
    {'name': 'Plaça de la Catedral', 'lat': 41.1188, 'lng': 1.2574, 'address': 'Plaça de la Catedral'},
    {'name': 'Carrer de la Tapineria', 'lat': 41.1191, 'lng': 1.2583, 'address': 'Carrer de la Tapineria'},
    {'name': 'Plaça del Rellotge', 'lat': 41.1187, 'lng': 1.2585, 'address': 'Plaça del Rellotge'},
    {'name': 'Carrer de Sant Miquel', 'lat': 41.1193, 'lng': 1.2580, 'address': 'Carrer de Sant Miquel'},
]

# Descripciones variadas por categoría
DESCRIPTIONS = {
    'excremento': [
        'Excrementos de palomas en el suelo',
        'Acumulación de excrementos en la zona',
        'Manchas de excrementos en la fachada',
        'Excrementos en el banco/banco público',
        'Zona con excrementos de palomas',
        'Excrementos en la acera',
        'Acumulación de excrementos en el tejado',
        'Excrementos en el monumento/escultura',
    ],
    'nido': [
        'Nido de palomas en el alero del edificio',
        'Nido activo en la cornisa',
        'Nido en el balcón',
        'Nido en el tejado',
        'Nido en la fachada del edificio',
        'Nido en el monumento histórico',
        'Nido en el árbol',
        'Nido en la estructura del edificio',
    ],
    'plumas': [
        'Plumas de palomas en el suelo',
        'Acumulación de plumas',
        'Plumas en la zona',
        'Restos de plumas',
    ],
    'escombreries_desbordades': [
        'Contenedor de basura desbordado',
        'Basura acumulada fuera del contenedor',
        'Contenedor lleno con basura alrededor',
        'Basura desbordada en la calle',
        'Contenedor de reciclaje desbordado',
        'Basura acumulada en la zona',
        'Contenedor sin capacidad disponible',
    ],
    'vertidos': [
        'Vertido ilegal de residuos',
        'Basura vertida en zona no autorizada',
        'Vertido de escombros',
        'Residuos vertidos en el suelo',
        'Vertido de materiales de construcción',
        'Basura vertida en zona verde',
        'Vertido ilegal detectado',
    ],
    'otro': [
        'Problema relacionado con palomas',
        'Otro problema de palomas',
        'Situación relacionada con palomas',
        'Otro problema urbano',
    ]
}

def generate_seed_data(num_items=50):
    """Generate seed data for inventory items"""
    app = create_app()
    
    with app.app_context():
        # Get admin user or create a dummy user for reporting
        admin_user = User.query.filter_by(email='hola@tarracograf.cat').first()
        if not admin_user:
            print("⚠️  Admin user not found. Creating items without reporter...")
            reporter_id = None
        else:
            reporter_id = admin_user.id
        
        # Categories and subcategories with weights
        # Distribution: 
        #   palomas: 40% excremento, 35% nido, 25% plumas (100% total)
        #   basura: 65% escombreries_desbordades, 35% vertidos (100% total)
        category_subcategory_map = [
            ('palomas', 'excremento')] * 20 + [
            ('palomas', 'nido')] * 17 + [
            ('palomas', 'plumas')] * 13 + [
            ('basura', 'escombreries_desbordades')] * 13 + [
            ('basura', 'vertidos')] * 7
        
        # Status distribution for realism:
        # 60% approved (visible on map)
        # 20% pending (awaiting approval)
        # 10% resolved (already fixed)
        # 5% active (legacy/old items)
        # 5% rejected (not valid)
        statuses = ['approved'] * 30 + ['pending'] * 10 + ['resolved'] * 5 + ['active'] * 3 + ['rejected'] * 2
        
        # Image probability: 40% of items will have images
        items_created = 0
        images_downloaded = 0
        
        for i in range(num_items):
            # Select random location
            location = random.choice(TARRAGONA_LOCATIONS)
            
            # Add small random offset to coordinates (to simulate different points in same area)
            lat_offset = random.uniform(-0.002, 0.002)  # ~200m variation
            lng_offset = random.uniform(-0.002, 0.002)
            
            latitude = location['lat'] + lat_offset
            longitude = location['lng'] + lng_offset
            
            # Select random category and subcategory
            category, subcategory = random.choice(category_subcategory_map)
            
            # Select random status
            status = random.choice(statuses)
            
            # Select random description (using subcategory as key)
            description = random.choice(DESCRIPTIONS[subcategory])
            
            # Random creation date (last 30 days)
            days_ago = random.randint(0, 30)
            created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
            
            # For resolved items, set updated_at to a later date
            if status == 'resolved':
                resolved_days_ago = random.randint(0, days_ago)
                updated_at = datetime.now(timezone.utc) - timedelta(days=resolved_days_ago)
            else:
                updated_at = created_at
            
            # Check if item already exists at this location (avoid duplicates)
            # Use a slightly larger radius to avoid too many duplicates
            existing = InventoryItem.query.filter(
                db.func.abs(InventoryItem.latitude - latitude) < 0.0005,
                db.func.abs(InventoryItem.longitude - longitude) < 0.0005,
                InventoryItem.category == category,
                InventoryItem.subcategory == subcategory
            ).first()
            
            if existing:
                continue  # Skip if similar item already exists at this location
            
            # 40% chance of having an image
            image_path = None
            if random.random() < 0.4:
                try:
                    # Use placeholder images from picsum.photos (random nature/urban images)
                    # Different image sizes for different subcategories
                    image_sizes = {
                        'excremento': (400, 300),
                        'nido': (300, 300),
                        'plumas': (300, 200),
                        'escombreries_desbordades': (400, 300),
                        'vertidos': (400, 300),
                        'otro': (400, 300)
                    }
                    width, height = image_sizes.get(subcategory, (400, 300))
                    
                    # Use a seed based on item data to get consistent images
                    seed = hash(f"{category}_{subcategory}_{latitude}_{longitude}") % 1000
                    image_url = f"https://picsum.photos/seed/{seed}/{width}/{height}"
                    
                    # Download image
                    filename = f"seed_{datetime.now().timestamp()}_{items_created}_{category}_{subcategory}.jpg"
                    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                    
                    # Ensure upload folder exists
                    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                    
                    # Download and save image
                    urllib.request.urlretrieve(image_url, file_path)
                    image_path = filename
                    images_downloaded += 1
                except Exception as e:
                    # If image download fails, continue without image
                    print(f"  ⚠️  Could not download image for item {items_created}: {e}")
                    image_path = None
            
            # Create item with random status
            item = InventoryItem(
                category=category,
                subcategory=subcategory,
                description=description,
                latitude=latitude,
                longitude=longitude,
                address=location['address'],
                status=status,  # Random status for realism
                importance_count=random.randint(0, 5) if status in ['approved', 'active'] else 0,  # Only approved/active items can have votes
                reporter_id=reporter_id,
                created_at=created_at,
                updated_at=updated_at,
                image_path=image_path  # Add image path if available
            )
            
            # Intentar asignar sección automáticamente basándose en coordenadas
            try:
                item.assign_section()
            except Exception as e:
                # Si falla la asignación, continuar sin sección
                print(f"  ⚠️  Could not assign section for item at ({latitude}, {longitude}): {e}")
            
            db.session.add(item)
            items_created += 1
        
        db.session.commit()
        
        # Estadísticas de asignación de secciones
        items_with_section = InventoryItem.query.filter(InventoryItem.section_id.isnot(None)).count()
        
        print(f"✅ Created {items_created} inventory items")
        if images_downloaded > 0:
            print(f"   📷 Downloaded {images_downloaded} images")
        if items_with_section > 0:
            print(f"   🗺️  {items_with_section} items assigned to sections")
        print(f"   Categories distribution:")
        by_category = {}
        for item in InventoryItem.query.filter(
            InventoryItem.status.in_(['approved', 'active'])
        ).all():
            cat_key = f"{item.category}->{item.subcategory}"
            by_category[cat_key] = by_category.get(cat_key, 0) + 1
        for cat_key, count in sorted(by_category.items()):
            # Extract subcategory for emoji
            subcat = cat_key.split('->')[1] if '->' in cat_key else cat_key
            emoji = {
                'excremento': '💩', 
                'nido': '🪺', 
                'plumas': '🪶',
                'escombreries_desbordades': '🗑️',
                'vertidos': '💧',
                'otro': '📌'
            }.get(subcat, '📌')
            print(f"      {emoji} {cat_key}: {count}")
        
        print(f"   Status distribution:")
        by_status = {}
        for item in InventoryItem.query.all():
            by_status[item.status] = by_status.get(item.status, 0) + 1
        status_labels = {
            'pending': '⏳ Pendents',
            'approved': '✅ Aprovats',
            'active': '🟢 Actius',
            'resolved': '✔️ Resolts',
            'rejected': '❌ Rebutjats'
        }
        for status, count in sorted(by_status.items()):
            label = status_labels.get(status, status)
            print(f"      {label}: {count}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate seed data for inventory')
    parser.add_argument('--count', type=int, default=50, help='Number of items to create (default: 50)')
    parser.add_argument('--clear', action='store_true', help='Clear existing inventory items before creating new ones')
    
    args = parser.parse_args()
    
    app = create_app()
    with app.app_context():
        if args.clear:
            print("🗑️  Clearing existing inventory items...")
            InventoryItem.query.delete()
            db.session.commit()
            print("✅ Cleared existing items")
        
        print(f"🌱 Generating {args.count} inventory items...")
        generate_seed_data(args.count)

