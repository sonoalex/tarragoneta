# Configuración de Celery para Envío Asíncrono de Emails

Celery está configurado para enviar emails de forma asíncrona, mejorando la experiencia del usuario al no bloquear las peticiones HTTP.

## Requisitos

- Redis (broker y backend de resultados)
- Celery worker ejecutándose

## Configuración Local

### 1. Iniciar Redis con Docker

```bash
docker-compose up -d redis
```

O si Redis ya está instalado localmente:

```bash
redis-server
```

### 2. Variables de Entorno

Añade a tu `.env`:

```bash
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
USE_CELERY_FOR_EMAILS=True
```

### 3. Iniciar el Worker de Celery

En una terminal separada:

```bash
# Opción 1: Usando el script
python celery_worker.py

# Opción 2: Usando celery directamente
celery -A celery_worker.celery worker --loglevel=info
```

### 4. Iniciar la Aplicación Flask

En otra terminal:

```bash
./start.sh
```

## Configuración en Producción (Railway)

### 1. Añadir Servicio Redis

1. Añade un servicio Redis en Railway
2. Railway proporcionará la variable `REDIS_URL`

### 2. Variables de Entorno

Añade en Railway:

```bash
CELERY_BROKER_URL=${REDIS_URL}/0
CELERY_RESULT_BACKEND=${REDIS_URL}/0
USE_CELERY_FOR_EMAILS=True
```

### 3. Añadir Worker Process

En `Procfile`, añade:

```
worker: celery -A celery_worker.celery worker --loglevel=info
```

Railway detectará automáticamente el proceso `worker` y lo ejecutará.

## Deshabilitar Celery

Si quieres deshabilitar Celery y enviar emails de forma síncrona:

```bash
USE_CELERY_FOR_EMAILS=False
```

El sistema automáticamente usará envío síncrono como fallback.

## Verificar que Funciona

1. Envía un email (por ejemplo, registra un usuario)
2. Verifica los logs del worker de Celery
3. Deberías ver: `Email sent successfully via Celery to ...`

## Troubleshooting

### Redis no está disponible

Si Redis no está disponible, el sistema automáticamente usará envío síncrono y mostrará un warning en los logs.

### Worker no procesa tareas

- Verifica que Redis esté corriendo
- Verifica que `CELERY_BROKER_URL` esté correctamente configurado
- Verifica los logs del worker para errores

### Emails no se envían

- Verifica los logs del worker
- Verifica la configuración de SMTP
- Verifica que `EMAIL_PROVIDER` esté configurado correctamente

