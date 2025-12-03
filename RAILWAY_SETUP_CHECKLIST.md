# 🚂 Checklist de Configuración para Railway

## 📋 Antes de Desplegar

### 1. ✅ Verificar Cambios Locales
```bash
# Ver estado de cambios
git status

# Ver resumen de cambios
git diff --stat
```

### 2. 🔧 Servicios Necesarios en Railway

#### A. **Servicio Web** (Principal)
- **Tipo**: Web Service
- **Repositorio**: Conectado a tu repo
- **Build**: Automático (detecta `railway.json` y `requirements.txt`)
- **Start Command**: Configurado en `railway.json` (usa `parallel` para Celery + Gunicorn)

#### B. **PostgreSQL con PostGIS** ⚠️ **OBLIGATORIO**
- **Tipo**: Database → PostgreSQL
- **Railway automáticamente**:
  - Crea la base de datos
  - Configura `DATABASE_URL` como variable de entorno
  - **IMPORTANTE**: Necesitas habilitar PostGIS manualmente después de crear la DB

**Para habilitar PostGIS:**
1. Ve a tu servicio PostgreSQL en Railway
2. Abre la consola SQL (Railway → PostgreSQL → Data → Query)
3. Ejecuta:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

#### C. **Redis** ⚠️ **OBLIGATORIO** (para Celery)
- **Tipo**: Database → Redis
- **Railway automáticamente**:
  - Crea Redis
  - Configura `REDIS_URL` como variable de entorno
  - **NOTA**: La aplicación detecta automáticamente `REDIS_URL` y lo usa para Celery
  - **OPCIONAL**: Puedes configurar `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND` manualmente si prefieres

### 3. 🔐 Variables de Entorno Requeridas

#### Variables OBLIGATORIAS:
```bash
# Flask
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=tu-clave-secreta-muy-segura-aqui
SECURITY_PASSWORD_SALT=tu-salt-para-contraseñas

# Email Provider
EMAIL_PROVIDER=smtp

# SMTP (Hostinger)
MAIL_SERVER=smtp.hostinger.com
MAIL_PORT=465
MAIL_USE_TLS=False
MAIL_USE_SSL=True
MAIL_USERNAME=hola@tarracograf.cat
MAIL_PASSWORD=tu-contraseña-de-email-hostinger
MAIL_DEFAULT_SENDER=Tarracograf <hola@tarracograf.cat>
MAIL_TIMEOUT=10

# Admin
ADMIN_EMAIL=hola@tarracograf.cat
ADMIN_USER_EMAIL=hola@tarracograf.cat
ADMIN_PASSWORD=tu-contraseña-admin-segura

# Celery (Redis)
# OPCIÓN 1: Usar REDIS_URL automático (recomendado)
# Railway proporciona REDIS_URL automáticamente, la app lo detecta
# No necesitas configurar CELERY_BROKER_URL ni CELERY_RESULT_BACKEND

# OPCIÓN 2: Configurar manualmente (si prefieres)
# CELERY_BROKER_URL=redis://default:REDIS_PASSWORD@REDIS_HOST:REDIS_PORT/0
# CELERY_RESULT_BACKEND=redis://default:REDIS_PASSWORD@REDIS_HOST:REDIS_PORT/0

USE_CELERY_FOR_EMAILS=True

# URL Generation (para emails)
SERVER_NAME=tarracograf.cat
PREFERRED_URL_SCHEME=https

# Stripe (opcional, si usas pagos)
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Reports (opcional)
REPORT_PRICE_EUROS=1.0
```

#### Variables Automáticas de Railway:
- `DATABASE_URL` (PostgreSQL) - ✅ Automático
- `REDIS_URL` (Redis) - ✅ Automático (pero necesitas configurar `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND` manualmente)
- `PORT` - ✅ Automático
- `RAILWAY_ENVIRONMENT` - ✅ Automático

### 4. 🔗 Configurar Redis para Celery

**✅ AUTOMÁTICO**: La aplicación detecta automáticamente `REDIS_URL` proporcionado por Railway y lo usa para Celery. **No necesitas configurar nada manualmente**.

**Si prefieres configurar manualmente** (opcional):
```bash
# Obtén estos valores de Railway → Redis → Variables
CELERY_BROKER_URL=redis://default:REDIS_PASSWORD@REDIS_HOST:REDIS_PORT/0
CELERY_RESULT_BACKEND=redis://default:REDIS_PASSWORD@REDIS_HOST:REDIS_PORT/0
```

### 5. 📦 Volumen para Uploads (Opcional)

Si necesitas persistir archivos subidos:
1. Railway → Tu servicio web → Settings → Volumes
2. Añade un volumen montado en `static/uploads`

### 6. 🚀 Proceso de Despliegue

1. **Crear servicios en Railway**:
   - Web Service (conectado a tu repo)
   - PostgreSQL Database
   - Redis Database

2. **Configurar variables de entorno** (ver sección 3)

3. **Habilitar PostGIS** en PostgreSQL (ver sección 2.B)

4. **Redis se configura automáticamente** (Railway proporciona `REDIS_URL` y la app lo detecta)

5. **Desplegar**:
   - Railway detectará automáticamente los cambios
   - El build ejecutará `pip install -r requirements.txt`
   - El release phase ejecutará migraciones (si está configurado)
   - El start command ejecutará `parallel` con Celery + Gunicorn

### 7. ✅ Verificar Despliegue

Después del despliegue, verifica:

1. **Logs del servicio web**:
   - Deberías ver: "🚀 Starting Tarracograf in production mode..."
   - Deberías ver: "🌐 Compiling translations..."
   - Deberías ver: "✅ Starting Gunicorn server..."
   - Deberías ver: "celery -A celery_worker.celery worker" iniciando

2. **Logs de Celery**:
   - Deberías ver: "celery@..." iniciado
   - Deberías ver: "ready" cuando esté listo

3. **Base de datos**:
   - Conecta a PostgreSQL y verifica que las tablas estén creadas:
   ```sql
   \dt
   ```
   - Verifica que PostGIS esté habilitado:
   ```sql
   SELECT PostGIS_version();
   ```

4. **Redis**:
   - Verifica que Redis esté accesible desde el servicio web

5. **Aplicación web**:
   - Visita la URL de Railway
   - Deberías ver la página principal
   - Intenta registrarte o iniciar sesión

### 8. 🔧 Comandos Útiles en Railway

#### Importar GeoJSON zones:
```bash
# En Railway → Web Service → Deployments → View Logs → Terminal
flask import-zones
```

#### Calcular boundary de la ciudad:
```bash
flask calculate-boundary
```

#### Crear usuario admin (si no existe):
```bash
flask init-db
```

### 9. 🐛 Troubleshooting

#### Error: "PostGIS extension not found"
- Ve a PostgreSQL → Data → Query
- Ejecuta: `CREATE EXTENSION IF NOT EXISTS postgis;`

#### Error: "Celery worker not starting"
- Verifica que `REDIS_URL` esté configurado (Railway lo proporciona automáticamente)
- Si configuraste manualmente, verifica `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND`
- Verifica que Redis esté accesible
- Revisa logs del servicio web

#### Error: "Database connection failed"
- Verifica que `DATABASE_URL` esté configurado
- Verifica que PostgreSQL esté corriendo
- Verifica que PostGIS esté habilitado

#### Error: "Email sending failed"
- Verifica `MAIL_*` variables
- Verifica que `EMAIL_PROVIDER=smtp`
- Verifica que Celery worker esté corriendo (para emails async)

### 10. 📝 Notas Importantes

- **PostGIS**: Debe habilitarse manualmente después de crear PostgreSQL
- **Redis**: Se configura automáticamente (la app detecta `REDIS_URL` de Railway)
- **Parallel**: El `railway.json` usa `parallel` para ejecutar Celery y Gunicorn en el mismo servicio
- **Migrations**: Se ejecutan automáticamente en el release phase (si está configurado en `Procfile`)
- **Translations**: Se compilan automáticamente en `start_production.sh`

