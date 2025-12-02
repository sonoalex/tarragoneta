from datetime import datetime, timedelta
from pathlib import Path
import json
import re
from app.extensions import db, user_datastore
from app.models import User, Role, Initiative
from app.utils import generate_slug
from flask_security import hash_password, verify_password

# Check if PostGIS dependencies are available
try:
    from shapely.geometry import shape as shapely_shape
    POSTGIS_AVAILABLE = True
except ImportError:
    POSTGIS_AVAILABLE = False

def init_db_command():
    """Initialize the database using Flask-Migrate."""
    from flask_migrate import upgrade
    
    # Upgrade database to latest migration
    print("Upgrading database schema using migrations...")
    try:
        upgrade()
        print("✓ Database schema upgraded")
    except Exception as e:
        # If no migrations exist yet, create them
        if "Target database is not up to date" in str(e) or "Can't locate revision" in str(e):
            print("No migrations found. Please run 'flask db init' and 'flask db migrate' first.")
            print("Falling back to db.create_all()...")
            db.create_all()
        else:
            print(f"Error upgrading database: {e}")
            print("Falling back to db.create_all()...")
            db.create_all()
    
    # Create roles if they don't exist
    if not Role.query.first():
        print("Creating default roles...")
        admin_role = Role(name='admin', description='Administrator')
        user_role = Role(name='user', description='Regular User')
        moderator_role = Role(name='moderator', description='Moderator')
        
        db.session.add(admin_role)
        db.session.add(user_role)
        db.session.add(moderator_role)
        db.session.commit()
        print("✓ Roles created")
    
    # Create admin user if it doesn't exist
    from flask import current_app
    admin_email = current_app.config.get('ADMIN_USER_EMAIL', 'hola@tarracograf.cat')
    admin_password = current_app.config.get('ADMIN_PASSWORD')
    
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        if not admin_password:
            # Solo en desarrollo: usar password por defecto
            if current_app.config.get('ENV') == 'development':
                admin_password = 'admin123'
                print("Creating admin user (development)...")
            else:
                print("⚠️  ADMIN_PASSWORD not configured. Skipping admin user creation.")
                print("   Set ADMIN_PASSWORD environment variable for production.")
                return
        
        print("Creating admin user...")
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            # Use user_datastore.create_user - Flask-Security handles password hashing
            admin_user = user_datastore.create_user(
                email=admin_email,
                username='admin',
                password=admin_password,
                active=True,
                confirmed_at=datetime.now(),
                roles=[admin_role]
            )
            db.session.commit()
            print("✓ Admin user created")
            if current_app.config.get('ENV') == 'development':
                print(f"  Email: {admin_email}")
                print(f"  Password: {admin_password} (change after first login!)")
        else:
            print("✗ Admin role not found. Please create roles first.")
    else:
        # Ensure admin is active (don't reset password if user exists)
        print("Admin user exists. Verifying status...")
        if not admin_user.active:
            admin_user.active = True
            admin_user.confirmed_at = datetime.now()
            db.session.commit()
            print("  ✓ Admin user activated")
        else:
            print("  ✓ Admin user is active")
    
    print("Database initialized successfully!")

def create_sample_data():
    """Create sample data for testing."""
    from flask_babel import gettext as _
    
    # Sample initiatives with variety
    initiatives_data = [
        {
            'title': 'Gran Neteja de la Platja del Miracle',
            'description': 'Uneix-te a nosaltres per a una jornada de neteja a la nostra estimada platja. Portarem bosses i guants, només necessites portar la teva energia i compromís amb el medi ambient.',
            'location': 'Platja del Miracle, Tarragona',
            'category': 'limpieza',
            'date': datetime.now().date() + timedelta(days=7),
            'time': '10:00'
        },
        {
            'title': 'Plantació d\'Arbres al Parc de la Ciutat',
            'description': 'Ajuda\'ns a reverdir la nostra ciutat plantant nous arbres. Una activitat perfecta per a famílies i amants de la naturalesa.',
            'location': 'Parc de la Ciutat, Tarragona',
            'category': 'espacios_verdes',
            'date': datetime.now().date() + timedelta(days=14),
            'time': '09:30'
        },
        {
            'title': 'Taller de Reciclatge Creatiu',
            'description': 'Aprèn a transformar residus en art i objectes útils. Taller gratuït per a totes les edats.',
            'location': 'Centre Cívic de Torreforta',
            'category': 'reciclaje',
            'date': datetime.now().date() + timedelta(days=10),
            'time': '17:00'
        },
        {
            'title': 'Acció contra la Brossa Desbordada',
            'description': 'Identifiquem i reportem contenedors de brossa desbordats per millorar la gestió de residus a la ciutat.',
            'location': 'Diverses ubicacions, Tarragona',
            'category': 'basura_desbordada',
            'date': datetime.now().date() + timedelta(days=5),
            'time': '18:00'
        },
        {
            'title': 'Vigilància de Vertits Il·legals',
            'description': 'Xarxa de ciutadans per detectar i reportar vertits il·legals de residus en zones no autoritzades.',
            'location': 'Zones perifèriques, Tarragona',
            'category': 'vertidos',
            'date': datetime.now().date() + timedelta(days=12),
            'time': '11:00'
        },
        {
            'title': 'Bicicletada per la Mobilitat Sostenible',
            'description': 'Ruta en bicicleta per promoure la mobilitat sostenible i reivindicar més carrils bici a Tarragona.',
            'location': 'Rambla Nova, Tarragona',
            'category': 'movilidad',
            'date': datetime.now().date() + timedelta(days=21),
            'time': '10:00'
        },
        {
            'title': 'Taller d\'Educació Ambiental per a Nens',
            'description': 'Taller interactiu per ensenyar als més petits la importància del reciclatge i el respecte al medi ambient.',
            'location': 'Parc del Francolí, Tarragona',
            'category': 'educacion',
            'date': datetime.now().date() + timedelta(days=8),
            'time': '16:00'
        },
        {
            'title': 'Neteja del Centre Històric',
            'description': 'Jornada de neteja col·lectiva del centre històric de Tarragona per mantenir la nostra ciutat neta i cívica.',
            'location': 'Centre Històric, Tarragona',
            'category': 'cultura',
            'date': datetime.now().date() + timedelta(days=15),
            'time': '09:00'
        },
        {
            'title': 'Campanya de Sensibilització sobre Residus',
            'description': 'Acció social per sensibilitzar sobre la importància de gestionar correctament els residus i evitar vertits il·legals.',
            'location': 'Plaça de la Font, Tarragona',
            'category': 'social',
            'date': datetime.now().date() + timedelta(days=6),
            'time': '12:00'
        },
        {
            'title': 'Neteja de la Zona del Port',
            'description': 'Iniciativa per netejar la zona del port i les platges properes de residus i plàstics.',
            'location': 'Port de Tarragona',
            'category': 'limpieza',
            'date': datetime.now().date() + timedelta(days=20),
            'time': '08:00'
        }
    ]
    
    admin_user = User.query.filter_by(username='admin').first()
    
    if not admin_user:
        print("✗ Admin user not found. Please run 'flask init-db' first.")
        return
    
    created = 0
    for data in initiatives_data:
        # Check if initiative with same slug already exists
        base_slug = generate_slug(data['title'])
        slug = base_slug
        counter = 1
        while Initiative.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Add slug to data
        data['slug'] = slug
        # Admin-created initiatives are auto-approved
        data['status'] = 'approved'
        initiative = Initiative(creator_id=admin_user.id, **data)
        db.session.add(initiative)
        created += 1
    
    db.session.commit()
    print(f"✓ Created {created} sample initiatives")
    print("✓ Sample data created successfully!")

def parse_filename(filename):
    """Extraer distrito y sección del nombre del archivo"""
    # Formatos posibles:
    # - seccio1.geojson -> distrito del directorio, sección 1
    # - seccio1_districte1.geojson -> distrito 1, sección 1
    # - seccio12_districte4.geojson -> distrito 4, sección 12
    
    filename = Path(filename).stem  # Sin extensión
    
    # Buscar patrón: seccioX_districteY o seccioX
    match = re.match(r'seccio(\d+)(?:_districte(\d+))?', filename, re.IGNORECASE)
    if match:
        section_num = match.group(1)
        district_num = match.group(2)  # Puede ser None
        return section_num, district_num
    return None, None

def get_district_from_dir(dirname):
    """Extraer número de distrito del nombre del directorio"""
    match = re.search(r'districte(\d+)', dirname, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def load_geojson(filepath):
    """Cargar archivo GeoJSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def import_zones_from_geojson(geojson_dir='geojson_tarragona'):
    """Importar todas las zonas desde el directorio GeoJSON"""
    if not POSTGIS_AVAILABLE:
        print("❌ Error: GeoAlchemy2 y Shapely no están instalados")
        print("   Instala con: pip install GeoAlchemy2 Shapely")
        return False
    
    geojson_path = Path(geojson_dir)
    
    if not geojson_path.exists():
        print(f"❌ Error: Directorio {geojson_dir} no existe")
        return False
    
    print("=" * 70)
    print("🗺️  Importación de Zonas Administrativas desde GeoJSON")
    print("=" * 70)
    print()
    
    from app.models import District, Section
    
    # Verificar tipo de base de datos
    db_url = str(db.engine.url)
    is_postgresql = 'postgresql' in db_url
    
    if is_postgresql:
        # Verificar que PostGIS está disponible en PostgreSQL
        try:
            result = db.session.execute(db.text("SELECT PostGIS_version();"))
            postgis_version = result.scalar()
            print(f"✅ PostgreSQL con PostGIS: {postgis_version}")
        except Exception as e:
            print(f"⚠️  PostgreSQL detectado pero PostGIS no está disponible")
            print(f"   {e}")
            print()
            print("💡 Solución:")
            print("   Ejecuta: CREATE EXTENSION IF NOT EXISTS postgis;")
            print()
            print("   Continuando con WKT (texto) en lugar de PostGIS...")
    
    print()
    
    # Estadísticas
    districts_created = 0
    sections_created = 0
    sections_updated = 0
    errors = []
    
    # Recorrer directorios de distritos
    district_dirs = sorted([d for d in geojson_path.iterdir() if d.is_dir() and d.name.startswith('districte')])
    
    print(f"📁 Encontrados {len(district_dirs)} distritos")
    print()
    
    for district_dir in district_dirs:
        district_num = get_district_from_dir(district_dir.name)
        if not district_num:
            print(f"⚠️  No se pudo extraer número de distrito de: {district_dir.name}")
            continue
        
        district_code = district_num.zfill(2)  # '01', '02', etc.
        district_name = f"Districte {district_num}"
        
        # Crear o obtener distrito
        district = District.query.filter_by(code=district_code).first()
        if not district:
            district = District(code=district_code, name=district_name)
            db.session.add(district)
            db.session.flush()  # Para obtener el ID
            districts_created += 1
            print(f"✅ Creado: {district_name} (código: {district_code})")
        else:
            print(f"ℹ️  Existe: {district_name} (código: {district_code})")
        
        # Procesar archivos GeoJSON del distrito
        geojson_files = sorted(district_dir.glob('*.geojson'))
        print(f"   📄 {len(geojson_files)} archivos GeoJSON encontrados")
        
        for geojson_file in geojson_files:
            try:
                # Extraer información del nombre del archivo
                section_num, file_district_num = parse_filename(geojson_file.name)
                
                # Si el archivo no especifica distrito, usar el del directorio
                if not file_district_num:
                    file_district_num = district_num
                
                # Validar que el distrito del archivo coincide con el directorio
                if file_district_num != district_num:
                    print(f"   ⚠️  Advertencia: {geojson_file.name} tiene distrito {file_district_num} pero está en {district_dir.name}")
                
                if not section_num:
                    print(f"   ⚠️  No se pudo extraer número de sección de: {geojson_file.name}")
                    continue
                
                section_code = section_num.zfill(3)  # '001', '002', etc.
                
                # Cargar GeoJSON
                geojson_data = load_geojson(geojson_file)
                
                if not geojson_data.get('features'):
                    print(f"   ⚠️  {geojson_file.name}: No tiene features")
                    continue
                
                # Procesar cada feature (normalmente hay uno por archivo)
                for feature in geojson_data['features']:
                    geometry = feature.get('geometry')
                    properties = feature.get('properties', {})
                    
                    # Obtener códigos de las propiedades si están disponibles
                    prop_district = properties.get('cdis', '').zfill(2) if properties.get('cdis') else ''
                    prop_section = properties.get('csec', '').zfill(3) if properties.get('csec') else ''
                    
                    # Usar códigos de propiedades si están disponibles, sino usar los del nombre
                    final_district_code = prop_district if prop_district else district_code
                    final_section_code = prop_section if prop_section else section_code
                    
                    # Validar que el distrito coincide
                    if final_district_code != district_code:
                        print(f"   ⚠️  Advertencia: {geojson_file.name} tiene distrito {final_district_code} en properties pero está en {district_code}")
                        final_district_code = district_code  # Usar el del directorio
                    
                    # Convertir geometría a formato apropiado
                    if geometry and geometry.get('type') == 'Polygon':
                        shapely_geom = shapely_shape(geometry)
                        
                        # Siempre usar WKT (texto) para almacenar
                        # El campo polygon es Text, así que almacenamos como WKT
                        # Si necesitamos PostGIS, podemos convertir usando ST_GeomFromText en queries
                        polygon_value = shapely_geom.wkt
                        
                        # Buscar o crear sección
                        section = Section.query.filter_by(
                            district_code=final_district_code,
                            code=final_section_code
                        ).first()
                        
                        section_name = f"Secció {int(final_section_code)} - {district_name}"
                        
                        if section:
                            # Actualizar geometría existente
                            section.polygon = polygon_value
                            section.name = section_name
                            sections_updated += 1
                            print(f"   ✅ Actualizado: {section_name} ({final_district_code}-{final_section_code})")
                        else:
                            # Crear nueva sección
                            section = Section(
                                code=final_section_code,
                                district_code=final_district_code,
                                name=section_name,
                                polygon=polygon_value
                            )
                            db.session.add(section)
                            sections_created += 1
                            print(f"   ✅ Creado: {section_name} ({final_district_code}-{final_section_code})")
                    else:
                        errors.append(f"{geojson_file.name}: Geometría no es Polygon o está vacía")
                        print(f"   ⚠️  {geojson_file.name}: Geometría inválida")
            
            except Exception as e:
                error_msg = f"{geojson_file.name}: {str(e)}"
                errors.append(error_msg)
                print(f"   ❌ Error en {geojson_file.name}: {e}")
                import traceback
                traceback.print_exc()
        
        print()
    
    # Commit todos los cambios
    try:
        db.session.commit()
        print("=" * 70)
        print("📊 RESUMEN")
        print("=" * 70)
        print(f"  Distritos creados: {districts_created}")
        print(f"  Secciones creadas: {sections_created}")
        print(f"  Secciones actualizadas: {sections_updated}")
        print(f"  Total secciones: {sections_created + sections_updated}")
        print(f"  Errores: {len(errors)}")
        print()
        
        if errors:
            print("⚠️  Errores encontrados:")
            for error in errors[:10]:  # Mostrar solo los primeros 10
                print(f"   - {error}")
            if len(errors) > 10:
                print(f"   ... y {len(errors) - 10} más")
            print()
        
        # Verificar datos importados
        total_districts = District.query.count()
        total_sections = Section.query.count()
        print(f"✅ Verificación:")
        print(f"   Distritos en BD: {total_districts}")
        print(f"   Secciones en BD: {total_sections}")
        print()
        
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al hacer commit: {e}")
        import traceback
        traceback.print_exc()
        return False

