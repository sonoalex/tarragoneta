# 🌱 Tarragoneta - Plataforma de Iniciativas Ciudadanas

![Python](https://img.shields.io/badge/Python-3.8.1%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📋 Descripción

**Tarragoneta** es una plataforma web diseñada para conectar ciudadanos comprometidos con iniciativas que mejoren la ciudad de Tarragona. La aplicación facilita la organización y participación en actividades de limpieza, reciclaje, espacios verdes, y otras acciones cívicas.

### ✨ Características Principales

- **🔐 Sistema de Autenticación Robusto**: Implementado con Flask-Security-Too
- **👥 Gestión de Roles**: Administradores, moderadores y usuarios regulares
- **📝 Gestión de Iniciativas**: Crear, editar, eliminar y gestionar iniciativas cívicas
- **🤝 Participación Ciudadana**: Sistema de registro para participantes (registrados y anónimos)
- **💬 Sistema de Comentarios**: Los usuarios pueden comentar y discutir iniciativas
- **📊 Panel de Administración**: Dashboard completo con estadísticas y gestión
- **📱 Diseño Responsive**: Optimizado para dispositivos móviles y escritorio
- **🖼️ Gestión de Imágenes**: Carga y optimización automática de imágenes
- **🔍 Filtros y Búsqueda**: Filtrar iniciativas por categoría, estado y fecha
- **🛡️ Seguridad**: Protección CSRF, sanitización de HTML, y hash de contraseñas
- **🕊️ Inventario de Palomas**: Sistema colaborativo para mapear problemas relacionados con palomas
- **🗺️ Mapas Interactivos**: Visualización geográfica con Leaflet.js y OpenStreetMap
- **⭐ Sistema de Importancia**: Los usuarios pueden confirmar la importancia de los items reportados

## 🚀 Instalación

### Prerequisitos

- Python 3.8.1 o superior
- [uv](https://github.com/astral-sh/uv) (gestor de paquetes rápido) - ya instalado en el sistema

### Pasos de Instalación con uv

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/tarragoneta.git
cd tarragoneta
```

2. **Crear entorno virtual con uv**
```bash
# uv crea el entorno virtual
uv venv
```

3. **Activar el entorno virtual**
```bash
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate  # Windows
```

4. **Instalar dependencias**
```bash
# Usando uv pip (recomendado - más rápido)
uv pip install --python .venv/bin/python setuptools
uv pip install --python .venv/bin/python -r requirements.txt

# O activar el entorno y usar pip estándar
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate  # Windows
pip install setuptools
pip install -r requirements.txt
```

5. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

6. **Inicializar la base de datos**
```bash
flask init-db
```

7. **Compilar traducciones (necesario para i18n)**
```bash
python3 compile_translations.py
```

8. **Crear datos de ejemplo (opcional)**
```bash
flask create-sample-data
```

9. **Generar datos del inventario de palomas (opcional)**
```bash
# Generar 50 items de ejemplo
python seed_data.py --count 50

# Generar 100 items
python seed_data.py --count 100

# Limpiar inventario existente y generar nuevos datos
python seed_data.py --clear --count 50
```

10. **Ejecutar la aplicación**
```bash
flask run
```

La aplicación estará disponible en `http://localhost:5000`

### 🌍 Idiomas

La aplicación soporta **Catalán** (por defecto) y **Español**. Puedes cambiar el idioma usando el selector en la barra de navegación.

- **Idioma por defecto**: Catalán (ca)
- **Idiomas soportados**: Catalán (ca), Español (es)

### Instalación alternativa con pip (legacy)

Si prefieres usar pip tradicional:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## 🔧 Configuración

### Variables de Entorno Importantes

- `SECRET_KEY`: Clave secreta para sesiones (cambiar en producción)
- `DATABASE_URL`: URL de conexión a la base de datos
- `SECURITY_PASSWORD_SALT`: Salt para contraseñas
- `MAIL_SERVER`: Servidor SMTP para envío de correos
- `FLASK_DEBUG`: Activar modo debug (`true` para desarrollo, `false` para producción)
- `FLASK_ENV`: Entorno de Flask (`development` o `production`)
- `STRIPE_PUBLISHABLE_KEY`: Clave pública de Stripe para donaciones
- `STRIPE_SECRET_KEY`: Clave secreta de Stripe para donaciones
- `STRIPE_WEBHOOK_SECRET`: Secreto del webhook de Stripe (opcional)

### Credenciales por Defecto

- **Usuario Admin**: admin@tarragoneta.org
- **Contraseña**: admin123

⚠️ **Importante**: Cambiar estas credenciales en producción

## 📁 Estructura del Proyecto

```
tarragoneta/
│
├── app.py                  # Aplicación principal Flask
├── seed_data.py           # Script para generar datos de ejemplo del inventario
├── pyproject.toml         # Configuración del proyecto y dependencias (uv)
├── requirements.txt        # Dependencias del proyecto (legacy, para pip)
├── .env.example           # Ejemplo de variables de entorno
├── README.md              # Este archivo
│
├── app/                    # Módulo principal de la aplicación
│   ├── __init__.py        # Factory pattern para crear la app
│   ├── config.py          # Configuración
│   ├── models.py          # Modelos de base de datos
│   ├── forms.py           # Formularios
│   ├── utils.py           # Funciones de utilidad
│   ├── extensions.py     # Extensiones Flask
│   ├── cli.py             # Comandos CLI
│   └── routes/            # Blueprints (rutas)
│       ├── main.py       # Rutas principales
│       ├── initiatives.py # Rutas de iniciativas
│       ├── admin.py       # Rutas de administración
│       ├── donations.py   # Rutas de donaciones
│       └── inventory.py   # Rutas del inventario
│
├── static/                # Archivos estáticos
│   ├── css/
│   │   └── style.css     # Estilos personalizados
│   ├── uploads/          # Imágenes subidas
│   └── images/           # Imágenes del sitio
│
├── templates/             # Plantillas HTML
│   ├── base.html         # Plantilla base
│   ├── index.html        # Página principal
│   ├── initiative_detail.html
│   ├── about.html
│   ├── contact.html
│   ├── profile.html
│   │
│   ├── admin/            # Templates de administración
│   │   ├── dashboard.html
│   │   ├── new_initiative.html
│   │   ├── edit_initiative.html
│   │   └── users.html
│   │
│   ├── inventory/        # Templates del inventario
│   │   ├── map.html      # Mapa principal
│   │   ├── report.html   # Formulario de reporte
│   │   └── admin.html    # Panel de administración
│   │
│   ├── security/         # Templates de autenticación
│   │   ├── login.html
│   │   └── register.html
│   │
│   └── errors/           # Páginas de error
│       ├── 404.html
│       └── 500.html
│
└── migrations/           # Migraciones de base de datos
```

## 🎨 Tecnologías Utilizadas

### Backend
- **Flask 3.0.0**: Framework web principal
- **Flask-SQLAlchemy**: ORM para gestión de base de datos
- **Flask-Security-Too**: Autenticación y autorización
- **Flask-WTF**: Formularios con protección CSRF
- **Flask-Migrate**: Migraciones de base de datos
- **Pillow**: Procesamiento de imágenes
- **Bleach**: Sanitización de HTML

### Frontend
- **HTML5/CSS3**: Estructura y estilos
- **JavaScript**: Interactividad
- **Font Awesome**: Iconos
- **HTMX**: Interacciones dinámicas (opcional)
- **Diseño Responsive**: Mobile-first

## 📝 Logging y Debug

La aplicación incluye un sistema de logging configurado:

### Modo Desarrollo (DEBUG=True)
- Logs en consola con nivel DEBUG
- Información detallada de cada request
- Stack traces completos en errores
- Activación del debugger de Flask

### Modo Producción (DEBUG=False)
- Logs en archivo rotativo (`logs/tarragoneta.log`)
- Rotación automática (10MB por archivo, 10 backups)
- Nivel de log INFO
- Información de errores sin exponer detalles sensibles

### Configuración
```bash
# Desarrollo
export FLASK_DEBUG=true
export FLASK_ENV=development

# Producción
export FLASK_DEBUG=false
export FLASK_ENV=production
```

## 🔐 Seguridad

La aplicación implementa múltiples capas de seguridad:

- ✅ Autenticación basada en sesiones
- ✅ Hash de contraseñas con bcrypt
- ✅ Protección CSRF en todos los formularios
- ✅ Sanitización de entrada de usuario
- ✅ Validación de tipos de archivo
- ✅ Límites de tamaño de archivo
- ✅ Roles y permisos granulares
- ✅ Logging de eventos importantes

## 🚀 Deployment

### Despliegue en Railway

Railway es una plataforma de despliegue que facilita el proceso de publicación de aplicaciones Flask.

#### Prerequisitos

1. Cuenta en [Railway](https://railway.app)
2. Repositorio Git (GitHub, GitLab, etc.)

#### Pasos para desplegar

1. **Conectar el repositorio a Railway**
   - Ve a [Railway Dashboard](https://railway.app/dashboard)
   - Clic en "New Project" → "Deploy from GitHub repo"
   - Selecciona tu repositorio

2. **Configurar variables de entorno**
   En Railway, ve a tu proyecto → Variables y añade:
   ```
   FLASK_ENV=production
   SECRET_KEY=tu-clave-secreta-muy-segura-aqui
   SECURITY_PASSWORD_SALT=tu-salt-para-contraseñas
   ```
   
   Railway automáticamente proporciona:
   - `DATABASE_URL` (PostgreSQL)
   - `PORT` (puerto donde escuchar)

3. **Añadir base de datos PostgreSQL** (opcional pero recomendado)
   - En Railway Dashboard → "New" → "Database" → "Add PostgreSQL"
   - Railway automáticamente configurará `DATABASE_URL`

4. **Desplegar**
   - Railway detectará automáticamente el `Procfile`
   - El despliegue comenzará automáticamente
   - Las migraciones se ejecutarán en el primer despliegue

#### Archivos de configuración para Railway

- **`Procfile`**: Define cómo iniciar la aplicación
- **`railway.json`**: Configuración específica de Railway (opcional)
- **`runtime.txt`**: Versión de Python (opcional)
- **`requirements.txt`**: Dependencias Python

#### Variables de entorno recomendadas

```bash
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=genera-una-clave-secreta-segura
SECURITY_PASSWORD_SALT=genera-un-salt-seguro
STRIPE_PUBLISHABLE_KEY=tu-clave-publica-stripe
STRIPE_SECRET_KEY=tu-clave-secreta-stripe
STRIPE_WEBHOOK_SECRET=tu-webhook-secret-stripe
```

#### Inicializar la base de datos

Después del primer despliegue, conecta a tu servicio Railway y ejecuta:

```bash
railway run flask init-db
```

O usa el CLI de Railway:
```bash
railway connect
flask init-db
```

### Producción local con Gunicorn

```bash
# Con entorno activado
gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 2 "app:create_app()"
```

### Docker (Opcional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copiar archivos de configuración
COPY pyproject.toml ./
COPY requirements.txt ./

# Instalar dependencias con uv
RUN uv sync --frozen

COPY . .

CMD ["uv", "run", "gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

## 📊 Funcionalidades por Rol

### 👤 Usuario Regular
- Ver iniciativas públicas
- Participar en iniciativas
- Comentar en iniciativas
- Gestionar su perfil
- Ver historial de participación

### 👮 Moderador
- Todo lo del usuario regular
- Moderar comentarios
- Revisar participaciones

### 👨‍💼 Administrador
- Todo lo anterior
- Crear/editar/eliminar iniciativas
- Gestionar usuarios
- Ver estadísticas completas
- Acceso al panel de administración

## 🛣️ Roadmap

- [ ] Sistema de notificaciones por email
- [ ] API REST para aplicación móvil
- [ ] Integración con redes sociales
- [ ] Sistema de gamificación
- [ ] Mapa interactivo de iniciativas
- [ ] Chat en tiempo real
- [ ] Exportación de datos a PDF/Excel
- [ ] Sistema de badges/logros

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 👥 Equipo

- **Desarrollo**: [Tu Nombre]
- **Diseño**: [Diseñador]
- **Concepto**: Comunidad de Tarragona

## 📞 Contacto

- **Email**: info@tarragoneta.org
- **Website**: https://tarragoneta.org
- **Twitter**: @tarragoneta

## 🙏 Agradecimientos

- A todos los ciudadanos comprometidos con Tarragona
- A las asociaciones y colectivos locales
- A la comunidad open source

---

Hecho con 💚 para Tarragona
Hecho con 💚 para Tarragona