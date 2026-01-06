#!/usr/bin/env python
"""
Script para migrar los InventoryItem existentes a usar las relaciones many-to-many
con InventoryCategory.

Este script:
1. Mapea los códigos antiguos (español/castellano) a los nuevos (catalán)
2. Busca las categorías en InventoryCategory por code
3. Crea las relaciones en inventory_item_categories
4. Marca la categoría principal como is_primary=True

IMPORTANTE: Este script es idempotente - puede ejecutarse múltiples veces sin duplicar datos.
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path para importar app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.models import InventoryItem, InventoryCategory, inventory_item_categories
from app.extensions import db
from sqlalchemy import text

# Mapeo de códigos antiguos (en BD) a códigos nuevos (catalán en InventoryCategory)
CATEGORY_CODE_MAPPING = {
    # Categorías principales
    'palomas': 'coloms',
    'basura': 'contenidors',
    'perros': 'canis',
    'material_deteriorat': 'mobiliari_deteriorat',  # Fusionada
    'mobiliari_urba': 'mobiliari_deteriorat',  # Fusionada
    'bruticia': 'bruticia',
    'vegetacio': 'vegetacio',
    'infraestructura': 'infraestructura',
}

# Mapeo de subcategorías antiguas a nuevas
SUBCATEGORY_CODE_MAPPING = {
    # Palomas -> Coloms
    'nido': 'niu',
    'excremento': 'excrement',
        'plumas': 'ploma',
    # Basura -> Contenidors
    'vertidos': 'abocaments',
    'escombreries_desbordades': None,  # Ya no se usa (Container Points)
    'basura_desbordada': None,  # Ya no se usa (Container Points)
    # Perros -> Canis
    'excrements': 'excrements',  # Ya está en catalán
    'pixades': 'pixades',  # Ya está en catalán
    # Material Deteriorat -> Mobiliari Deteriorat
    'faroles': 'faroles',  # Ya está en catalán
    'bancs': 'bancs',  # Ya está en catalán
    'senyals': 'senyals',  # Ya está en catalán
    'paviment': 'paviment',  # Ya está en catalán
    # Mobiliari Urbà -> Mobiliari Deteriorat (fusionada)
    'papereres': 'papereres',  # Ya está en catalán
    'parades': 'parades',  # Ya está en catalán
    # Brutícia
    'terra': 'terra',  # Ya está en catalán
    'fulles': 'fulles',  # Ya está en catalán
    'grafit': 'grafit',  # Ya está en catalán
    # Vegetació
    'arbres': 'arbres',  # Ya está en catalán
    'arbustos': 'arbustos',  # Ya está en catalán
    'gespa': 'gespa',  # Ya está en catalán
    # Infraestructura
    'carreteres': 'carreteres',  # Ya está en catalán
    'voreres': 'voreres',  # Ya está en catalán
    'enllumenat': 'enllumenat',  # Ya está en catalán
    # General
    'otro': None,  # No se maneja
}


def get_category_by_code(code):
    """Obtiene una categoría por su código"""
    if not code:
        return None
    return InventoryCategory.query.filter_by(code=code, parent_id=None).first()


def get_subcategory_by_code(code, parent_category):
    """Obtiene una subcategoría por su código y parent"""
    if not code or not parent_category:
        return None
    return InventoryCategory.query.filter_by(
        code=code,
        parent_id=parent_category.id
    ).first()


def migrate_items():
    """Migra los items existentes a usar relaciones many-to-many"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Iniciando migración de items a categorías...")
        print()
        
        # Obtener todos los items
        items = InventoryItem.query.all()
        total_items = len(items)
        
        if total_items == 0:
            print("ℹ️  No hay items para migrar")
            return
        
        print(f"📦 Total de items a migrar: {total_items}")
        print()
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        errors = []
        
        for item in items:
            try:
                # Mapear códigos antiguos a nuevos
                new_category_code = CATEGORY_CODE_MAPPING.get(item.category)
                new_subcategory_code = SUBCATEGORY_CODE_MAPPING.get(item.subcategory)
                
                # Verificar si ya tiene relaciones (ya migrado)
                existing_relations = db.session.execute(
                    text("SELECT COUNT(*) FROM inventory_item_categories WHERE item_id = :item_id"),
                    {'item_id': item.id}
                ).scalar()
                
                if existing_relations > 0:
                    skipped_count += 1
                    continue
                
                # Validar mapeo
                if not new_category_code:
                    errors.append(f"Item {item.id}: categoría '{item.category}' no tiene mapeo")
                    error_count += 1
                    continue
                
                # Obtener categoría principal
                main_category = get_category_by_code(new_category_code)
                if not main_category:
                    errors.append(f"Item {item.id}: categoría '{new_category_code}' no encontrada en BD")
                    error_count += 1
                    continue
                
                # Verificar si tiene subcategoría válida
                subcategory = None
                if new_subcategory_code:
                    subcategory = get_subcategory_by_code(new_subcategory_code, main_category)
                    if not subcategory:
                        # Intentar buscar sin parent (por si acaso)
                        subcategory = InventoryCategory.query.filter_by(code=new_subcategory_code).first()
                
                # Crear relación con categoría principal (marcar como primary)
                db.session.execute(
                    text("""
                        INSERT INTO inventory_item_categories (item_id, category_id, is_primary, created_at)
                        VALUES (:item_id, :category_id, :is_primary, NOW())
                        ON CONFLICT (item_id, category_id) DO NOTHING
                    """),
                    {
                        'item_id': item.id,
                        'category_id': main_category.id,
                        'is_primary': True
                    }
                )
                
                # Crear relación con subcategoría si existe
                if subcategory:
                    db.session.execute(
                        text("""
                            INSERT INTO inventory_item_categories (item_id, category_id, is_primary, created_at)
                            VALUES (:item_id, :category_id, :is_primary, NOW())
                            ON CONFLICT (item_id, category_id) DO NOTHING
                        """),
                        {
                            'item_id': item.id,
                            'category_id': subcategory.id,
                            'is_primary': False
                        }
                    )
                
                # NOTA: No actualizamos los campos category y subcategory porque
                # estos campos se eliminarán en el último paso de la migración.
                # Por ahora, el código usa código legacy para compatibilidad.
                
                migrated_count += 1
                
                if migrated_count % 100 == 0:
                    db.session.commit()
                    print(f"   ✅ Migrados {migrated_count} items...")
            
            except Exception as e:
                error_count += 1
                errors.append(f"Item {item.id}: {str(e)}")
                db.session.rollback()
                continue
        
        # Commit final
        db.session.commit()
        
        # Resumen
        print()
        print("=" * 80)
        print("✅ MIGRACIÓN COMPLETADA")
        print("=" * 80)
        print(f"   Items migrados: {migrated_count}")
        print(f"   Items ya migrados (omitidos): {skipped_count}")
        print(f"   Errores: {error_count}")
        print()
        
        if errors:
            print("⚠️  ERRORES ENCONTRADOS:")
            for error in errors[:20]:  # Mostrar solo los primeros 20
                print(f"   - {error}")
            if len(errors) > 20:
                print(f"   ... y {len(errors) - 20} errores más")
            print()
        
        # Verificar resultados
        items_with_categories = db.session.execute(
            text("SELECT COUNT(DISTINCT item_id) FROM inventory_item_categories")
        ).scalar()
        
        print(f"📊 Items con categorías asociadas: {items_with_categories} de {total_items}")
        print()


if __name__ == '__main__':
    migrate_items()

