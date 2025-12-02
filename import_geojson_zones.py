#!/usr/bin/env python
"""
Script para importar zonas administrativas (distritos y secciones) desde GeoJSON
a PostgreSQL con PostGIS

Este script es un wrapper que usa el comando CLI de Flask.
Para usar directamente el comando CLI, ejecuta:
    flask import-zones
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.cli import import_zones_from_geojson

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        success = import_zones_from_geojson()
        if success:
            print("✅ Importación completada exitosamente")
            sys.exit(0)
        else:
            print("❌ Importación falló")
            sys.exit(1)

