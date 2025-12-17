"""
CLI commands registration
"""
import click
from flask import current_app
from sqlalchemy import text
from datetime import datetime
from app.cli import init_db_command, create_sample_data, import_zones_from_geojson, create_admin_user_command, assign_sections_to_items
from app.models import CityBoundary
from app.extensions import db


def register_cli_commands(app):
    """Register all CLI commands"""
    @app.cli.command('init-db')
    def init_db():
        """Initialize the database using Flask-Migrate."""
        init_db_command()
    
    @app.cli.command('create-admin')
    @click.option('--email', default=None, help='Email del usuario admin (default: hola@tarracograf.cat o ADMIN_USER_EMAIL)')
    @click.option('--password', default=None, help='Password del usuario admin (default: ADMIN_PASSWORD o admin123 en desarrollo)')
    @click.option('--username', default=None, help='Username del usuario admin (default: admin)')
    def create_admin(email, password, username):
        """Create or update admin user."""
        success = create_admin_user_command(email=email, password=password, username=username)
        if not success:
            raise click.ClickException("Error al crear usuario admin")
    
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

    @app.cli.command('fix-sections-geometry')
    @click.option('--snap', default=0.00001, show_default=True, help='Tamaño de la rejilla para SnapToGrid (grados). 0.00001 ≈ 1-2m.')
    @click.option('--buffer', 'buffer_dist', default=0.00005, show_default=True, help='Buffer positivo para cerrar gaps (grados). 0.00005 ≈ 5-6m en Tarragona.')
    @click.option('--recalculate-boundary/--no-recalculate-boundary', default=True, show_default=True, help='Recalcular el boundary de ciudad después de ajustar secciones.')
    def fix_sections_geometry(snap, buffer_dist, recalculate_boundary):
        """Ajustar geometrías de secciones para cerrar micro-gaps (SnapToGrid + Buffer)."""
        with app.app_context():
            sql = text("""
                UPDATE section
                SET polygon = ST_AsText(
                  ST_Buffer(
                    ST_SnapToGrid(
                      ST_Buffer(ST_MakeValid(ST_GeomFromText(polygon,4326)), 0),
                      :snap
                    ),
                    :buffer_dist
                  )
                )
            """)
            try:
                result = db.session.execute(sql, {'snap': snap, 'buffer_dist': buffer_dist})
                db.session.commit()
                updated = result.rowcount if result.rowcount is not None else 'desconocido'
                print(f"✅ Secciones ajustadas (SnapToGrid={snap}, Buffer={buffer_dist}). Filas afectadas: {updated}")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error ajustando secciones: {e}")
                raise

            if recalculate_boundary:
                boundary_wkt = CityBoundary.calculate_boundary()
                if boundary_wkt:
                    existing = CityBoundary.query.first()
                    if existing:
                        existing.polygon = boundary_wkt
                        existing.updated_at = datetime.utcnow()
                        print('✅ Boundary actualizado tras ajuste de secciones')
                    else:
                        existing = CityBoundary(name='Tarragona', polygon=boundary_wkt)
                        db.session.add(existing)
                        print('✅ Boundary creado tras ajuste de secciones')
                    db.session.commit()
                else:
                    print('⚠️  No se pudo recalcular el boundary tras el ajuste de secciones')
    
    @app.cli.command('fix-sections-gaps-smart')
    @click.option('--max-gap', default=0.0001, show_default=True, help='Distancia máxima para considerar gap (grados). 0.0001 ≈ 10-15m.')
    @click.option('--buffer', default=0.00002, show_default=True, help='Buffer para cerrar gaps (grados). 0.00002 ≈ 2-3m.')
    @click.option('--recalculate-boundary/--no-recalculate-boundary', default=True, show_default=True, help='Recalcular boundary tras ajuste.')
    def fix_sections_gaps_smart(max_gap, buffer, recalculate_boundary):
        """
        Cerrar gaps solo entre secciones que están cerca pero no se tocan.
        Usa ST_Distance/ST_DWithin para detectar gaps pequeños y aplica buffer solo a esas secciones.
        """
        with app.app_context():
            # Primero, contar cuántas secciones tienen gaps detectados
            # Usar ST_Distance > 0 para asegurar que hay un gap real (no solo que no se toquen)
            min_gap = max_gap * 0.1  # Solo considerar gaps mayores al 10% del max_gap
            count_sql = text("""
                SELECT COUNT(DISTINCT section_id) as count
                FROM (
                    SELECT s1.id as section_id
                    FROM section s1, section s2
                    WHERE s1.id < s2.id
                      AND ST_DWithin(
                          ST_MakeValid(ST_GeomFromText(s1.polygon, 4326)),
                          ST_MakeValid(ST_GeomFromText(s2.polygon, 4326)),
                          :max_gap
                      )
                      AND ST_Distance(
                          ST_MakeValid(ST_GeomFromText(s1.polygon, 4326)),
                          ST_MakeValid(ST_GeomFromText(s2.polygon, 4326))
                      ) > :min_gap
                    UNION
                    SELECT s2.id as section_id
                    FROM section s1, section s2
                    WHERE s1.id < s2.id
                      AND ST_DWithin(
                          ST_MakeValid(ST_GeomFromText(s1.polygon, 4326)),
                          ST_MakeValid(ST_GeomFromText(s2.polygon, 4326)),
                          :max_gap
                      )
                      AND ST_Distance(
                          ST_MakeValid(ST_GeomFromText(s1.polygon, 4326)),
                          ST_MakeValid(ST_GeomFromText(s2.polygon, 4326))
                      ) > :min_gap
                ) as gaps
            """)
            
            count_result = db.session.execute(count_sql, {'max_gap': max_gap, 'min_gap': min_gap}).scalar()
            print(f"🔍 Secciones con gaps detectados (distancia > {min_gap}): {count_result}")
            
            if count_result == 0:
                print("ℹ️  No se encontraron gaps significativos. Las secciones ya están correctamente ajustadas.")
                return
            
            # Aplicar buffer solo a secciones con gaps
            sql = text("""
                WITH sections_with_gaps AS (
                    SELECT DISTINCT s1.id as section_id
                    FROM section s1, section s2
                    WHERE s1.id < s2.id
                      AND ST_DWithin(
                          ST_MakeValid(ST_GeomFromText(s1.polygon, 4326)),
                          ST_MakeValid(ST_GeomFromText(s2.polygon, 4326)),
                          :max_gap
                      )
                      AND ST_Distance(
                          ST_MakeValid(ST_GeomFromText(s1.polygon, 4326)),
                          ST_MakeValid(ST_GeomFromText(s2.polygon, 4326))
                      ) > :min_gap
                    UNION
                    SELECT DISTINCT s2.id as section_id
                    FROM section s1, section s2
                    WHERE s1.id < s2.id
                      AND ST_DWithin(
                          ST_MakeValid(ST_GeomFromText(s1.polygon, 4326)),
                          ST_MakeValid(ST_GeomFromText(s2.polygon, 4326)),
                          :max_gap
                      )
                      AND ST_Distance(
                          ST_MakeValid(ST_GeomFromText(s1.polygon, 4326)),
                          ST_MakeValid(ST_GeomFromText(s2.polygon, 4326))
                      ) > :min_gap
                )
                UPDATE section s
                SET polygon = ST_AsText(
                    ST_Buffer(
                        ST_MakeValid(ST_GeomFromText(s.polygon, 4326)),
                        :buffer
                    )
                )
                WHERE s.id IN (SELECT section_id FROM sections_with_gaps)
            """)
            
            result = db.session.execute(sql, {'max_gap': max_gap, 'min_gap': min_gap, 'buffer': buffer})
            db.session.commit()
            updated = result.rowcount if result.rowcount is not None else 'desconocido'
            print(f"✅ Secciones con gaps ajustadas: {updated}")
            
            if recalculate_boundary:
                boundary_wkt = CityBoundary.calculate_boundary()
                if boundary_wkt:
                    existing = CityBoundary.query.first()
                    if existing:
                        existing.polygon = boundary_wkt
                        existing.updated_at = datetime.utcnow()
                        print('✅ Boundary actualizado tras ajuste de gaps')
                    else:
                        existing = CityBoundary(name='Tarragona', polygon=boundary_wkt)
                        db.session.add(existing)
                        print('✅ Boundary creado tras ajuste de gaps')
                    db.session.commit()
                else:
                    print('⚠️  No se pudo recalcular el boundary tras ajuste de gaps')

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
    
    @app.cli.command('sync-migrations')
    def sync_migrations():
        """Sincronizar alembic_version cuando se migra de migraciones antiguas a nuevas.
        
        Este comando actualiza alembic_version a la migración inicial (6d646413299d)
        si detecta que hay tablas existentes pero la revisión en alembic_version
        es antigua y ya no existe en el código.
        
        Útil cuando se consolida múltiples migraciones en una sola migración inicial.
        """
        from sqlalchemy import inspect, text
        from flask_migrate import current as get_current_revision
        
        with app.app_context():
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Verificar si hay tablas de aplicación
            has_app_tables = any(t in existing_tables for t in ['user', 'role', 'initiative', 'inventory_item'])
            has_alembic_version = 'alembic_version' in existing_tables
            
            if not has_app_tables:
                print("ℹ️  No hay tablas de aplicación. No es necesario sincronizar.")
                return
            
            if not has_alembic_version:
                print("ℹ️  No hay tabla alembic_version. Las migraciones se crearán normalmente.")
                return
            
            # Obtener revisión actual
            try:
                current_rev = get_current_revision()
                print(f"📋 Revisión actual en alembic_version: {current_rev}")
            except Exception as e:
                print(f"⚠️  No se pudo obtener la revisión actual: {e}")
                return
            
            # Verificar si la revisión actual existe en las migraciones disponibles
            from flask_migrate import history
            try:
                migration_history = history()
                available_revisions = [m.revision for m in migration_history]
                
                if current_rev in available_revisions:
                    print(f"✅ La revisión {current_rev} existe en las migraciones. No es necesario sincronizar.")
                    return
                
                # La revisión actual no existe en el código nuevo
                print(f"⚠️  La revisión {current_rev} no existe en las migraciones actuales.")
                print("   Esto significa que se migró de migraciones antiguas a nuevas.")
                print("   Actualizando alembic_version a la migración inicial (6d646413299d)...")
                
                # Actualizar a la migración inicial
                conn = db.engine.connect()
                conn.execute(text("UPDATE alembic_version SET version_num = '6d646413299d'"))
                conn.commit()
                conn.close()
                
                print("✅ alembic_version actualizado a 6d646413299d")
                print("   Ahora puedes ejecutar 'flask db upgrade' para aplicar las nuevas migraciones.")
                
            except Exception as e:
                print(f"❌ Error al sincronizar: {e}")
                raise
    
    @app.cli.command('assign-sections')
    def assign_sections():
        """Asignar secciones a items del inventario que no tienen section_id asignado."""
        success = assign_sections_to_items()
        if not success:
            raise click.ClickException("Error al asignar secciones a items")

