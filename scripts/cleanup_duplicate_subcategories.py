#!/usr/bin/env python
"""
Script para limpiar subcategorías duplicadas/legacy en la base de datos.

Este script:
1. Identifica subcategorías legacy que deben ser desactivadas
2. Desactiva subcategorías duplicadas (ej: 'plomes' cuando existe 'ploma')
3. Muestra un resumen de los cambios
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path para importar app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.models import InventoryCategory
from app.extensions import db

# Mapeo de subcategorías legacy que deben ser desactivadas
# (la clave es la legacy, el valor es la correcta)
LEGACY_SUBCATEGORIES = {
    'plomes': 'ploma',  # 'plomes' es legacy, 'ploma' es la correcta
    'plumas': 'ploma',  # 'plumas' es legacy, 'ploma' es la correcta
}

def cleanup_duplicate_subcategories():
    """Desactiva subcategorías legacy duplicadas"""
    app = create_app()
    
    with app.app_context():
        print("🧹 Iniciando limpieza de subcategorías duplicadas/legacy...")
        print()
        
        deactivated_count = 0
        
        # Para cada subcategoría legacy
        for legacy_code, correct_code in LEGACY_SUBCATEGORIES.items():
            # Buscar la subcategoría legacy
            legacy_subcat = InventoryCategory.query.filter_by(
                code=legacy_code,
                is_active=True
            ).first()
            
            if not legacy_subcat:
                print(f"   ⏭️  Subcategoría legacy '{legacy_code}' no encontrada o ya desactivada")
                continue
            
            # Verificar que existe la subcategoría correcta
            correct_subcat = InventoryCategory.query.filter_by(
                code=correct_code,
                is_active=True
            ).first()
            
            if not correct_subcat:
                print(f"   ⚠️  Subcategoría correcta '{correct_code}' no encontrada. No se desactivará '{legacy_code}'")
                continue
            
            # Verificar que ambas tienen el mismo parent
            if legacy_subcat.parent_id != correct_subcat.parent_id:
                print(f"   ⚠️  '{legacy_code}' y '{correct_code}' tienen diferentes parents. No se desactivará '{legacy_code}'")
                continue
            
            # Desactivar la subcategoría legacy
            legacy_subcat.is_active = False
            deactivated_count += 1
            print(f"   ✅ Desactivada subcategoría legacy '{legacy_code}' (correcta: '{correct_code}')")
        
        if deactivated_count > 0:
            db.session.commit()
            print()
            print(f"✅ Limpieza completada: {deactivated_count} subcategorías desactivadas")
        else:
            print()
            print("✅ No se encontraron subcategorías duplicadas para desactivar")
        
        print()
        print("=" * 80)
        print("📊 Estado actual de subcategorías por categoría:")
        print("=" * 80)
        
        # Mostrar estado actual
        main_categories = InventoryCategory.query.filter_by(
            parent_id=None,
            is_active=True
        ).order_by(InventoryCategory.sort_order).all()
        
        for main_cat in main_categories:
            subcategories = InventoryCategory.query.filter_by(
                parent_id=main_cat.id
            ).order_by(InventoryCategory.sort_order).all()
            
            active_subs = [s for s in subcategories if s.is_active]
            inactive_subs = [s for s in subcategories if not s.is_active]
            
            print(f"\n{main_cat.code}:")
            if active_subs:
                print(f"   ✅ Activas: {', '.join([s.code for s in active_subs])}")
            if inactive_subs:
                print(f"   ❌ Inactivas: {', '.join([s.code for s in inactive_subs])}")


if __name__ == '__main__':
    cleanup_duplicate_subcategories()

