# 🏠 Configuración para Desarrollo Local

Esta guía te ayudará a configurar Tarracograf para desarrollo local.

## 📋 Requisitos Previos

1. Python 3.9+ instalado
2. `uv` instalado (gestor de paquetes)
3. Cuenta de email en Hostinger configurada

## 🚀 Configuración Rápida

### 1. Copiar archivo de configuración

```bash
cp env.example .env
```

### 2. Configurar variables de entorno en `.env`

Edita el archivo `.env` y configura:

```bash
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# Database (PostgreSQL con PostGIS para desarrollo local)
# Usa Docker Compose para iniciar PostgreSQL:
# docker-compose up -d
DATABASE_URL=postgresql://tarracograf:tarracograf_dev@localhost:5432/tarracograf

# Email Provider (usar SMTP para local)
EMAIL_PROVIDER=smtp

# SMTP Configuration (Hostinger)
MAIL_SERVER=smtp.hostinger.com
MAIL_PORT=465
MAIL_USE_TLS=False
MAIL_USE_SSL=True
MAIL_USERNAME=hola@tarracograf.cat
MAIL_PASSWORD=tu-contraseña-de-email
MAIL_DEFAULT_SENDER=Tarracograf <hola@tarracograf.cat>
MAIL_SUPPRESS_SEND=False

# Admin user
ADMIN_USER_EMAIL=hola@tarracograf.cat
ADMIN_PASSWORD=admin123
```

### 3. Probar configuración de email

```bash
python test_email_config.py
```

Deberías ver:
- ✅ SSL connection established
- ✅ Authentication successful!
- ✅ Test email sent successfully

### 4. Iniciar la aplicación

```bash
./start.sh
```

O manualmente:

```bash
# Activar entorno virtual
source .venv/bin/activate

# Inicializar base de datos
uv run python init_db.py

# Compilar traducciones
uv run python compile_translations.py

# Iniciar servidor
uv run flask run --host=0.0.0.0 --port=5000 --debug
```

## 🔑 Credenciales por Defecto

- **URL**: http://127.0.0.1:5000
- **Email Admin**: `hola@tarracograf.cat`
- **Password Admin**: `admin123` (cambiar después del primer login)

## 📧 Configuración de Email

### Hostinger SMTP

La aplicación está configurada para usar Hostinger SMTP por defecto:

- **Servidor**: `smtp.hostinger.com`
- **Puerto**: `465` (SSL) o `587` (TLS)
- **Usuario**: Tu email completo (ej: `hola@tarracograf.cat`)
- **Contraseña**: La contraseña de tu cuenta de email

### Probar Email

Ejecuta el script de prueba:

```bash
python test_email_config.py
```

Este script:
1. Verifica la configuración
2. Prueba la conexión SMTP
3. Envía un email de prueba a tu dirección

## 🐛 Solución de Problemas

### Error de conexión SMTP

1. Verifica que `MAIL_PASSWORD` esté correctamente configurado
2. Prueba cambiar a TLS (puerto 587):
   ```bash
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USE_SSL=False
   ```

### Error de autenticación

1. Verifica que el email y contraseña sean correctos
2. Asegúrate de usar la contraseña de la cuenta de email, no la del panel de Hostinger

### Base de datos no se crea

1. Verifica que tengas permisos de escritura en el directorio
2. Ejecuta manualmente: `uv run python init_db.py`

## 📚 Más Información

- [Configuración SMTP Hostinger](./SETUP_HOSTINGER_SMTP.md)
- [Configuración de Email](./EMAILS_LIST.md)

