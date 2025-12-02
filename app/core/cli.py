"""
CLI commands registration
"""
import click
from app.cli import init_db_command, create_sample_data, import_zones_from_geojson


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

