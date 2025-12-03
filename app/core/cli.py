"""
CLI commands registration
"""
import click
from flask import current_app
from app.cli import init_db_command, create_sample_data, import_zones_from_geojson
from app.models import CityBoundary
from app.extensions import db
from datetime import datetime


def register_cli_commands(app):
    """Register all CLI commands"""
    @app.cli.command('init-db')
    def init_db():
        """Initialize the database using Flask-Migrate."""
        init_db_command()
    
    @app.cli.command('create-sample-data')
    def create_sample():
        """Create sample data for testing."""
        create_sample_data()
    
    @app.cli.command('import-zones')
    @click.option('--geojson-dir', default='geojson_tarragona', help='Directorio con los archivos GeoJSON')
    def import_zones_command(geojson_dir):
        """Importar zonas administrativas (distritos y secciones) desde GeoJSON."""
        success = import_zones_from_geojson(geojson_dir)
        if not success:
            raise click.ClickException("Error al importar zonas")
    
    @app.cli.command('calculate-boundary')
    def calculate_boundary():
        """Calculate and save the city boundary (convex hull of all sections)"""
        with app.app_context():
            boundary_wkt = CityBoundary.calculate_boundary()
            if boundary_wkt:
                existing = CityBoundary.query.first()
                if existing:
                    existing.polygon = boundary_wkt
                    existing.updated_at = datetime.utcnow()
                    current_app.logger.info('✅ City boundary updated')
                else:
                    existing = CityBoundary(name='Tarragona', polygon=boundary_wkt)
                    db.session.add(existing)
                    current_app.logger.info('✅ City boundary created')
                db.session.commit()
                print(f'✅ City boundary calculated and saved ({len(boundary_wkt)} characters)')
            else:
                print('❌ Could not calculate city boundary')
                current_app.logger.error('Failed to calculate city boundary')

