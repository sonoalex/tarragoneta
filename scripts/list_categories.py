#!/usr/bin/env python
"""
Script para listar todas las categorías y subcategorías hardcoded actuales.
Este script muestra la estructura completa antes de migrar a BD.
"""

# Estructura de categorías y subcategorías (sincronizada con seed_categories.py)
# Iconos en formato Font Awesome (fa-*)
CATEGORIES_DATA = {
    'coloms': {
        'icon': 'fa-dove',
        'name_ca': 'Coloms',
        'subcategories': [
            {'code': 'niu', 'icon': 'fa-home', 'name_ca': 'Niu'},
            {'code': 'excrement', 'icon': 'fa-biohazard', 'name_ca': 'Excrement'},
            {'code': 'ploma', 'icon': 'fa-feather', 'name_ca': 'Ploma'},
        ]
    },
    'contenidors': {
        'icon': 'fa-trash',
        'name_ca': 'Contenidors',
        'subcategories': [
            {'code': 'abocaments', 'icon': 'fa-tint', 'name_ca': 'Abocaments'},
            {'code': 'deixadesa', 'icon': 'fa-trash-alt', 'name_ca': 'Deixadesa'},
        ]
    },
    'canis': {
        'icon': 'fa-dog',
        'name_ca': 'Canis',
        'subcategories': [
            {'code': 'excrements', 'icon': 'fa-poop', 'name_ca': 'Excrements'},
            {'code': 'pixades', 'icon': 'fa-tint', 'name_ca': 'Pixades'},
        ]
    },
    'mobiliari_deteriorat': {
        'icon': 'fa-tools',
        'name_ca': 'Mobiliari Deteriorat',
        'subcategories': [
            {'code': 'faroles', 'icon': 'fa-lightbulb', 'name_ca': 'Faroles'},
            {'code': 'bancs', 'icon': 'fa-chair', 'name_ca': 'Bancs'},
            {'code': 'senyals', 'icon': 'fa-sign', 'name_ca': 'Senyals'},
            {'code': 'paviment', 'icon': 'fa-road', 'name_ca': 'Paviment'},
            {'code': 'papereres', 'icon': 'fa-trash', 'name_ca': 'Papereres'},
            {'code': 'parades', 'icon': 'fa-bus', 'name_ca': 'Parades'},
        ]
    },
    'bruticia': {
        'icon': 'fa-broom',
        'name_ca': 'Brutícia',
        'subcategories': [
            {'code': 'terra', 'icon': 'fa-mountain', 'name_ca': 'Terra'},
            {'code': 'fulles', 'icon': 'fa-leaf', 'name_ca': 'Fulles'},
            {'code': 'grafit', 'icon': 'fa-spray-can', 'name_ca': 'Grafit'},
        ]
    },
    'vandalisme': {
        'icon': 'fa-spray-can',
        'name_ca': 'Vandalisme',
        'subcategories': [
            {'code': 'pintades', 'icon': 'fa-spray-can', 'name_ca': 'Pintades'},
        ]
    },
    'vegetacio': {
        'icon': 'fa-tree',
        'name_ca': 'Vegetació',
        'subcategories': [
            {'code': 'arbres', 'icon': 'fa-tree', 'name_ca': 'Arbres'},
            {'code': 'arbustos', 'icon': 'fa-seedling', 'name_ca': 'Arbustos'},
            {'code': 'gespa', 'icon': 'fa-grass', 'name_ca': 'Gespa'},
        ]
    },
    'infraestructura': {
        'icon': 'fa-building',
        'name_ca': 'Infraestructura',
        'subcategories': [
            {'code': 'carreteres', 'icon': 'fa-road', 'name_ca': 'Carreteres'},
            {'code': 'voreres', 'icon': 'fa-walking', 'name_ca': 'Voreres'},
            {'code': 'enllumenat', 'icon': 'fa-lightbulb', 'name_ca': 'Enllumenat'},
        ]
    },
}

# Categorías/subcategorías que ya no se usan (para referencia)
DEPRECATED = {
    'escombreries_desbordades': {
        'note': 'Removed - now handled by Container Points',
        'alias': 'basura_desbordada'
    }
}

def print_categories():
    """Imprime todas las categorías y subcategorías de forma estructurada"""
    print("=" * 80)
    print("CATEGORÍAS Y SUBCATEGORÍAS (CÓDIGOS EN CATALÁN)")
    print("=" * 80)
    print()
    
    total_categories = len(CATEGORIES_DATA)
    total_subcategories = sum(len(cat['subcategories']) for cat in CATEGORIES_DATA.values())
    
    print(f"📊 RESUMEN:")
    print(f"   - Categorías principales: {total_categories}")
    print(f"   - Subcategorías totales: {total_subcategories}")
    print()
    
    for idx, (code, data) in enumerate(CATEGORIES_DATA.items(), 1):
        print(f"{idx}. {data['icon']} {data['name_ca']} (code: '{code}')")
        print(f"   Subcategorías ({len(data['subcategories'])}):")
        
        for sub_idx, subcat in enumerate(data['subcategories'], 1):
            note = f" - {subcat.get('note', '')}" if 'note' in subcat else ''
            print(f"   {sub_idx}. {subcat['icon']} {subcat['name_ca']} (code: '{subcat['code']}'){note}")
        
        print()
    
    if DEPRECATED:
        print("⚠️  CATEGORÍAS DEPRECADAS (no se incluirán en la migración):")
        for code, info in DEPRECATED.items():
            print(f"   - {code}: {info['note']}")
            if 'alias' in info:
                print(f"     Alias: {info['alias']}")
        print()
    
    print("=" * 80)
    print("NOTAS:")
    print("  - Todos los códigos están en catalán")
    print("  - Los iconos están en formato Font Awesome (fa-*)")
    print("  - 'material_deteriorat' y 'mobiliari_urba' han sido fusionadas en 'mobiliari_deteriorat'")
    print("  - 'escombreries_desbordades' ya no se usa (ahora se gestiona con Container Points)")
    print("=" * 80)

if __name__ == '__main__':
    print_categories()
