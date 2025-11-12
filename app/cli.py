from datetime import datetime, timedelta
from app.extensions import db, user_datastore
from app.models import User, Role, Initiative
from app.utils import generate_slug
from flask_security import hash_password, verify_password

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
    admin_email = current_app.config.get('ADMIN_USER_EMAIL', 'admin@tarragoneta.org')
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
            'category': 'basura_desborda',
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

