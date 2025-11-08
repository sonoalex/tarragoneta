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
    admin_user = User.query.filter_by(email='admin@tarragoneta.org').first()
    if not admin_user:
        print("Creating admin user...")
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            # Use user_datastore.create_user - Flask-Security handles password hashing
            admin_user = user_datastore.create_user(
                email='admin@tarragoneta.org',
                username='admin',
                password='admin123',  # Flask-Security hashes this automatically
                active=True,
                confirmed_at=datetime.now(),
                roles=[admin_role]
            )
            db.session.commit()
            print("✓ Admin user created")
            print("  Email: admin@tarragoneta.org")
            print("  Password: admin123")
        else:
            print("✗ Admin role not found. Please create roles first.")
    else:
        # Ensure admin is active and password is correct
        print("Admin user exists. Verifying password...")
        if not verify_password('admin123', admin_user.password):
            print("  Password hash invalid. Regenerating...")
            admin_user.password = hash_password('admin123')
            admin_user.active = True
            admin_user.confirmed_at = datetime.now()
            db.session.commit()
            print("  ✓ Password regenerated")
        else:
            print("  ✓ Password is valid")
    
    print("Database initialized successfully!")

def create_sample_data():
    """Create sample data for testing."""
    # Sample initiatives
    initiatives_data = [
        {
            'title': 'Gran Limpieza de la Playa del Miracle',
            'description': 'Únete a nosotros para una jornada de limpieza en nuestra querida playa. Traeremos bolsas y guantes, solo necesitas traer tu energía y compromiso con el medio ambiente.',
            'location': 'Playa del Miracle, Tarragona',
            'category': 'limpieza',
            'date': datetime.now().date() + timedelta(days=7),
            'time': '10:00'
        },
        {
            'title': 'Plantación de Árboles en el Parque de la Ciudad',
            'description': 'Ayúdanos a reverdecer nuestra ciudad plantando nuevos árboles. Una actividad perfecta para familias y amantes de la naturaleza.',
            'location': 'Parc de la Ciutat, Tarragona',
            'category': 'espacios_verdes',
            'date': datetime.now().date() + timedelta(days=14),
            'time': '09:30'
        },
        {
            'title': 'Taller de Reciclaje Creativo',
            'description': 'Aprende a transformar residuos en arte y objetos útiles. Taller gratuito para todas las edades.',
            'location': 'Centro Cívico de Torreforta',
            'category': 'reciclaje',
            'date': datetime.now().date() + timedelta(days=10),
            'time': '17:00'
        }
    ]
    
    admin_user = User.query.filter_by(username='admin').first()
    
    if not admin_user:
        print("✗ Admin user not found. Please run 'flask init-db' first.")
        return
    
    for data in initiatives_data:
        # Generate slug from title
        base_slug = generate_slug(data['title'])
        slug = base_slug
        counter = 1
        # Ensure slug is unique
        while Initiative.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Add slug to data
        data['slug'] = slug
        initiative = Initiative(creator_id=admin_user.id, **data)
        db.session.add(initiative)
    
    db.session.commit()
    print("✓ Sample data created successfully!")

