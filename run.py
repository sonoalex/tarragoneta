#!/usr/bin/env python
"""
Tarragoneta - Initialization and Startup Script
This script sets up the database and starts the application
"""

import os
import sys
from app import create_app
from app.extensions import db, user_datastore
from app.models import Role, User, Initiative
from datetime import datetime, timedelta
from flask_security import hash_password

app = create_app()

def init_database():
    """Initialize the database with default data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if roles exist
        if not Role.query.first():
            print("Creating default roles...")
            
            # Create roles
            admin_role = Role(name='admin', description='Administrator with full access')
            user_role = Role(name='user', description='Regular user')
            moderator_role = Role(name='moderator', description='Moderator with limited admin access')
            
            db.session.add_all([admin_role, user_role, moderator_role])
            db.session.commit()
            
            print("✓ Roles created")
        
        # Check if admin user exists
        if not User.query.filter_by(email='admin@tarragoneta.org').first():
            print("Creating admin user...")
            
            admin_role = Role.query.filter_by(name='admin').first()
            
            # Create admin user
            admin_user = user_datastore.create_user(
                email='admin@tarragoneta.org',
                username='admin',
                password=hash_password('admin123'),
                active=True,
                confirmed_at=datetime.now(),
                roles=[admin_role]
            )
            
            db.session.commit()
            print("✓ Admin user created")
            print("  Email: admin@tarragoneta.org")
            print("  Password: admin123")
            print("  ⚠️  Please change the password after first login!")
        
        # Create sample initiatives if none exist
        if not Initiative.query.first():
            print("Creating sample initiatives...")
            
            admin_user = User.query.filter_by(email='admin@tarragoneta.org').first()
            
            sample_initiatives = [
                {
                    'title': '🧹 Gran Limpieza de la Playa del Miracle',
                    'description': '''¡Únete a nosotros para una jornada de limpieza en nuestra querida playa!
                    
La Playa del Miracle es uno de los tesoros de Tarragona, pero necesita nuestra ayuda. 
Cada año, toneladas de residuos llegan a nuestras costas afectando la vida marina y la belleza de nuestro litoral.

**¿Qué haremos?**
- Recogeremos residuos de la playa y zonas adyacentes
- Clasificaremos los materiales para su correcto reciclaje
- Documentaremos los tipos de residuos encontrados
- Sensibilizaremos a los bañistas sobre la importancia de mantener limpias nuestras playas

**¿Qué necesitas traer?**
- Ganas de ayudar y buen humor
- Protección solar y gorra
- Agua para mantenerte hidratado
- Guantes (aunque proporcionaremos algunos)

Nosotros proporcionaremos bolsas, herramientas de recogida y guantes adicionales. 
Al finalizar, habrá un pequeño refrigerio para todos los participantes.

¡Cada grano de arena cuenta! Tu participación marca la diferencia.''',
                    'location': 'Playa del Miracle, Tarragona',
                    'category': 'limpieza',
                    'date': datetime.now().date() + timedelta(days=7),
                    'time': '10:00',
                    'creator_id': admin_user.id
                },
                {
                    'title': '🌳 Plantación de Árboles en el Parc de la Ciutat',
                    'description': '''Ayúdanos a reverdecer nuestra ciudad plantando nuevos árboles autóctonos.

Los árboles son los pulmones de nuestra ciudad. No solo mejoran la calidad del aire, 
sino que también proporcionan sombra, reducen la temperatura urbana y embellecen nuestros espacios.

**Actividades programadas:**
- Plantación de 50 nuevos árboles autóctonos
- Taller sobre cuidado de árboles urbanos
- Actividades para niños sobre la importancia de los árboles
- Creación de un "bosque de los deseos" comunitario

**Especies que plantaremos:**
- Pinos mediterráneos
- Encinas
- Algarrobos
- Olivos

Esta es una actividad perfecta para familias. Los niños aprenderán sobre la naturaleza 
mientras contribuyen activamente a mejorar su entorno.

Ven con ropa cómoda que se pueda ensuciar. ¡Nosotros ponemos las herramientas y los árboles!''',
                    'location': 'Parc de la Ciutat, Tarragona',
                    'category': 'espacios_verdes',
                    'date': datetime.now().date() + timedelta(days=14),
                    'time': '09:30',
                    'creator_id': admin_user.id
                },
                {
                    'title': '♻️ Taller de Reciclaje Creativo para Familias',
                    'description': '''Aprende a transformar residuos en arte y objetos útiles en este taller gratuito.

¿Sabías que muchos de los objetos que tiramos pueden tener una segunda vida? 
En este taller aprenderemos técnicas creativas para reutilizar materiales que normalmente acabarían en la basura.

**¿Qué aprenderás?**
- Técnicas de upcycling y reciclaje creativo
- Crear macetas con botellas de plástico
- Hacer bolsas reutilizables con camisetas viejas
- Construir juguetes con materiales reciclados
- Decoración navideña sostenible

**Materiales que puedes traer:**
- Botellas de plástico limpias
- Latas vacías
- Camisetas viejas
- Revistas y periódicos
- Cartón de cajas

El taller es totalmente gratuito y apto para todas las edades. 
Los menores de 12 años deben venir acompañados de un adulto.

¡Descubre cómo tu creatividad puede ayudar al planeta!''',
                    'location': 'Centro Cívico de Torreforta',
                    'category': 'reciclaje',
                    'date': datetime.now().date() + timedelta(days=10),
                    'time': '17:00',
                    'creator_id': admin_user.id
                },
                {
                    'title': '🚴 Ruta Ciclista Sostenible por Tarragona',
                    'description': '''Únete a nuestra ruta ciclista para promover la movilidad sostenible en la ciudad.

Pedalearemos juntos por las principales vías ciclables de Tarragona, demostrando que 
la bicicleta es una alternativa real y saludable para moverse por la ciudad.

**Itinerario:**
- Salida: Plaza Imperial Tarraco
- Paseo por la Rambla Nova
- Recorrido por el Serrallo
- Visita al Parque del Francolí
- Llegada: Playa Larga

**Objetivos:**
- Promover el uso de la bicicleta como transporte diario
- Identificar puntos de mejora en la infraestructura ciclista
- Crear comunidad entre ciclistas urbanos
- Demostrar que Tarragona puede ser una ciudad bike-friendly

Distancia total: 15 km (nivel fácil)
Duración estimada: 2 horas con paradas

Trae tu bicicleta, casco y agua. Si no tienes bici, contacta con nosotros 
y te ayudaremos a conseguir una prestada.''',
                    'location': 'Plaza Imperial Tarraco',
                    'category': 'movilidad',
                    'date': datetime.now().date() + timedelta(days=5),
                    'time': '11:00',
                    'creator_id': admin_user.id
                },
                {
                    'title': '📚 Charla: Educación Ambiental en las Escuelas',
                    'description': '''Conferencia abierta sobre cómo integrar la educación ambiental en el currículo escolar.

Dirigida a profesores, padres y cualquier persona interesada en la educación ambiental 
de las nuevas generaciones.

**Temas a tratar:**
- Importancia de la educación ambiental desde temprana edad
- Estrategias para integrar la sostenibilidad en el aula
- Proyectos prácticos para estudiantes
- Recursos y materiales disponibles
- Casos de éxito en otras ciudades

**Ponentes:**
- María García - Experta en pedagogía ambiental
- Joan Martí - Director de proyectos educativos sostenibles
- Ana López - Profesora y activista ambiental

La charla incluirá una sesión de preguntas y respuestas, y se proporcionarán 
materiales didácticos gratuitos para los asistentes.

Entrada libre hasta completar aforo. Se expedirá certificado de asistencia.''',
                    'location': 'Biblioteca Pública de Tarragona',
                    'category': 'educacion',
                    'date': datetime.now().date() + timedelta(days=20),
                    'time': '18:30',
                    'creator_id': admin_user.id
                }
            ]
            
            for data in sample_initiatives:
                initiative = Initiative(**data)
                db.session.add(initiative)
            
            db.session.commit()
            print(f"✓ {len(sample_initiatives)} sample initiatives created")
        
        print("\n✅ Database initialization complete!")
        print("=" * 50)

def run_application():
    """Run the Flask application"""
    print("\n🚀 Starting Tarragoneta application...")
    print(f"🌐 Application will be available at: http://localhost:5000")
    print("=" * 50)
    print("Press CTRL+C to stop the server\n")
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )

def main():
    """Main function"""
    print("=" * 50)
    print("🌱 TARRAGONETA - Civic Initiatives Platform")
    print("=" * 50)
    
    # Check if this is the first run
    db_path = 'tarragoneta.db'
    first_run = not os.path.exists(db_path)
    
    if first_run or '--init' in sys.argv:
        print("\n📦 Initializing database...")
        init_database()
    
    if '--no-run' not in sys.argv:
        run_application()

if __name__ == '__main__':
    main()