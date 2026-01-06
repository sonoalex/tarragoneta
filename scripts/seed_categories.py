#!/usr/bin/env python
"""
Script para migrar categorías y subcategorías hardcoded a la base de datos.

Este script:
1. Crea todas las categorías principales
2. Crea todas las subcategorías con sus relaciones parent
3. Asigna created_by al primer admin encontrado
4. Establece sort_order para mantener orden lógico

IMPORTANTE: Este script es idempotente - puede ejecutarse múltiples veces sin duplicar datos.
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path para importar app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.models import InventoryCategory, User, Role, RoleEnum
from app.extensions import db

# Estructura de categorías y subcategorías
# Iconos en formato Font Awesome (fa-*)
CATEGORIES_DATA = [
    {
        'code': 'coloms',
        'icon': 'fa-dove',
        'sort_order': 1,
        'subcategories': [
            {'code': 'niu', 'icon': 'fa-home', 'sort_order': 1},
            {'code': 'excrement', 'icon': 'fa-biohazard', 'sort_order': 2},
            {'code': 'ploma', 'icon': 'fa-feather', 'sort_order': 3},
        ]
    },
    {
        'code': 'contenidors',
        'icon': 'fa-trash',
        'sort_order': 2,
        'subcategories': [
            # 'escombreries_desbordades' removed - now handled by Container Points
            {'code': 'abocaments', 'icon': 'fa-tint', 'sort_order': 1},
            {'code': 'deixadesa', 'icon': 'fa-trash-alt', 'sort_order': 2},
        ]
    },
    {
        'code': 'canis',
        'icon': 'fa-dog',
        'sort_order': 3,
        'subcategories': [
            {'code': 'excrements', 'icon': 'fa-poop', 'sort_order': 1},
            {'code': 'pixades', 'icon': 'fa-tint', 'sort_order': 2},
        ]
    },
    {
        'code': 'mobiliari_deteriorat',
        'icon': 'fa-tools',
        'sort_order': 4,
        'subcategories': [
            {'code': 'faroles', 'icon': 'fa-lightbulb', 'sort_order': 1},
            {'code': 'bancs', 'icon': 'fa-chair', 'sort_order': 2},
            {'code': 'senyals', 'icon': 'fa-sign', 'sort_order': 3},
            {'code': 'paviment', 'icon': 'fa-road', 'sort_order': 4},
            {'code': 'papereres', 'icon': 'fa-trash', 'sort_order': 5},
            {'code': 'parades', 'icon': 'fa-bus', 'sort_order': 6},
        ]
    },
    {
        'code': 'bruticia',
        'icon': 'fa-broom',
        'sort_order': 5,
        'subcategories': [
            {'code': 'terra', 'icon': 'fa-mountain', 'sort_order': 1},
            {'code': 'fulles', 'icon': 'fa-leaf', 'sort_order': 2},
            {'code': 'grafit', 'icon': 'fa-spray-can', 'sort_order': 3},
        ]
    },
    {
        'code': 'vandalisme',
        'icon': 'fa-spray-can',
        'sort_order': 6,
        'subcategories': [
            {'code': 'pintades', 'icon': 'fa-spray-can', 'sort_order': 1},
        ]
    },
    {
        'code': 'vegetacio',
        'icon': 'fa-tree',
        'sort_order': 7,
        'subcategories': [
            {'code': 'arbres', 'icon': 'fa-tree', 'sort_order': 1},
            {'code': 'arbustos', 'icon': 'fa-seedling', 'sort_order': 2},
            {'code': 'gespa', 'icon': 'fa-grass', 'sort_order': 3},
        ]
    },
    {
        'code': 'infraestructura',
        'icon': 'fa-building',
        'sort_order': 8,
        'subcategories': [
            {'code': 'carreteres', 'icon': 'fa-road', 'sort_order': 1},
            {'code': 'voreres', 'icon': 'fa-walking', 'sort_order': 2},
            {'code': 'enllumenat', 'icon': 'fa-lightbulb', 'sort_order': 3},
        ]
    },
]


def get_admin_user():
    """Obtiene el primer usuario admin, o None si no existe"""
    admin_role = Role.query.filter_by(name=RoleEnum.ADMIN.value).first()
    if not admin_role:
        return None
    
    admin_user = User.query.join(User.roles).filter(
        Role.id == admin_role.id
    ).first()
    
    return admin_user


def seed_categories():
    """Migra las categorías hardcoded a la base de datos"""
    app = create_app()
    
    with app.app_context():
        print("🌱 Iniciando migración de categorías a base de datos...")
        print()
        
        # Obtener usuario admin
        admin_user = get_admin_user()
        if not admin_user:
            print("⚠️  ADVERTENCIA: No se encontró ningún usuario admin.")
            print("   Las categorías se crearán sin created_by_id")
            print()
        else:
            print(f"✅ Usuario admin encontrado: {admin_user.email} (ID: {admin_user.id})")
            print()
        
        created_categories = 0
        created_subcategories = 0
        updated_categories = 0
        updated_subcategories = 0
        skipped_categories = 0
        skipped_subcategories = 0
        
        # Crear categorías principales
        print("📁 Creando categorías principales...")
        category_objects = {}
        
        for cat_data in CATEGORIES_DATA:
            # Verificar si ya existe
            existing = InventoryCategory.query.filter_by(code=cat_data['code']).first()
            if existing:
                # Actualizar icono si es diferente
                if existing.icon != cat_data['icon']:
                    old_icon = existing.icon
                    existing.icon = cat_data['icon']
                    updated_categories += 1
                    print(f"   🔄 Actualizado icono de categoría '{cat_data['code']}': {old_icon} → {cat_data['icon']}")
                else:
                    print(f"   ⏭️  Categoría '{cat_data['code']}' ya existe, omitiendo...")
                    skipped_categories += 1
                category_objects[cat_data['code']] = existing
                continue
            
            # Crear categoría principal
            category = InventoryCategory(
                code=cat_data['code'],
                icon=cat_data['icon'],
                parent_id=None,
                is_active=True,
                sort_order=cat_data['sort_order'],
                created_by_id=admin_user.id if admin_user else None
            )
            
            db.session.add(category)
            db.session.flush()  # Para obtener el ID
            
            category_objects[cat_data['code']] = category
            created_categories += 1
            print(f"   ✅ Creada categoría: {cat_data['icon']} {cat_data['code']} (ID: {category.id})")
        
        db.session.commit()
        print(f"   📊 Categorías principales: {created_categories} creadas, {updated_categories} actualizadas, {skipped_categories} sin cambios")
        print()
        
        # Crear subcategorías
        print("📂 Creando subcategorías...")
        
        for cat_data in CATEGORIES_DATA:
            parent_category = category_objects[cat_data['code']]
            
            for subcat_data in cat_data['subcategories']:
                # Verificar si ya existe
                existing = InventoryCategory.query.filter_by(
                    code=subcat_data['code'],
                    parent_id=parent_category.id
                ).first()
                
                if existing:
                    # Actualizar icono si es diferente
                    if existing.icon != subcat_data['icon']:
                        old_icon = existing.icon
                        existing.icon = subcat_data['icon']
                        updated_subcategories += 1
                        print(f"   🔄 Actualizado icono de subcategoría '{subcat_data['code']}': {old_icon} → {subcat_data['icon']}")
                    else:
                        print(f"   ⏭️  Subcategoría '{subcat_data['code']}' (parent: {cat_data['code']}) ya existe, omitiendo...")
                        skipped_subcategories += 1
                    continue
                
                # Crear subcategoría
                subcategory = InventoryCategory(
                    code=subcat_data['code'],
                    icon=subcat_data['icon'],
                    parent_id=parent_category.id,
                    is_active=True,
                    sort_order=subcat_data['sort_order'],
                    created_by_id=admin_user.id if admin_user else None
                )
                
                db.session.add(subcategory)
                created_subcategories += 1
                print(f"   ✅ Creada subcategoría: {subcat_data['icon']} {subcat_data['code']} (parent: {cat_data['code']})")
        
        db.session.commit()
        print(f"   📊 Subcategorías: {created_subcategories} creadas, {updated_subcategories} actualizadas, {skipped_subcategories} sin cambios")
        print()
        
        # Resumen final
        print("=" * 80)
        print("✅ MIGRACIÓN COMPLETADA")
        print("=" * 80)
        print(f"   Categorías principales: {created_categories} creadas, {updated_categories} actualizadas")
        print(f"   Subcategorías: {created_subcategories} creadas, {updated_subcategories} actualizadas")
        print(f"   Total categorías en BD: {InventoryCategory.query.filter_by(parent_id=None).count()}")
        print(f"   Total subcategorías en BD: {InventoryCategory.query.filter(InventoryCategory.parent_id.isnot(None)).count()}")
        print()
        
        print("✅ Categorías fusionadas: 'material_deteriorat' y 'mobiliari_urba' → 'mobiliari_deteriorat'")
        print()


if __name__ == '__main__':
    seed_categories()
