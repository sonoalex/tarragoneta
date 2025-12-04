# 🚂 Configuración del Worker de Celery en Railway

## Problema: Worker se congela con "Trying again..."

Si ves el mensaje `Trying again in 32.00 seconds... (20/100)`, significa que Celery no puede conectarse a Redis.

## Solución: Configurar servicio worker con acceso a Redis

### Paso 1: Crear servicio worker en Railway

1. Ve a tu proyecto en Railway
2. Click en **"+ New"** → **"Empty Service"** (o duplica el servicio web)
3. Nombre: `Worker` o `Celery Worker`

### Paso 2: Conectar Redis al servicio worker

**IMPORTANTE**: El servicio worker necesita acceso al mismo Redis que el servicio web.

1. En el servicio worker, ve a **"Settings"** → **"Variables"**
2. Busca la variable `REDIS_URL` (debería estar disponible si Redis está conectado al proyecto)
3. Si no está, añádela manualmente:
   - Ve a tu servicio Redis en Railway
   - Copia el `REDIS_URL` de las variables de entorno
   - Añádelo al servicio worker

### Paso 3: Configurar Start Command

En el servicio worker:
- **Start Command**: `bash start_worker.sh`
- **Tipo**: Background Worker (no necesita PORT)

### Paso 4: Variables de entorno necesarias

El servicio worker necesita estas variables (las mismas que el servicio web):

**Obligatorias:**
- `REDIS_URL` o `CELERY_BROKER_URL` - Conexión a Redis
- `DATABASE_URL` - Conexión a PostgreSQL
- `SECRET_KEY` - Clave secreta de Flask
- `FLASK_ENV=production`

**Opcionales pero recomendadas:**
- `CELERY_RESULT_BACKEND` - Si quieres resultados persistentes
- `EMAIL_PROVIDER=smtp`
- `MAIL_*` - Configuración SMTP
- Todas las demás variables del servicio web

### Paso 5: Verificar conexión

El script `start_worker.sh` ahora verifica:
- ✅ Que `REDIS_URL` o `CELERY_BROKER_URL` esté configurado
- ✅ Que Flask app se puede crear
- ✅ Logs más detallados para debugging

## Troubleshooting

### Error: "Trying again in 32.00 seconds..."

**Causa**: Celery no puede conectarse a Redis

**Solución**:
1. Verifica que `REDIS_URL` esté configurado en el servicio worker
2. Verifica que Redis esté corriendo y accesible
3. Verifica que ambos servicios (web y worker) usen el mismo Redis

### Error: "Cannot create Flask app"

**Causa**: Faltan variables de entorno o hay error en la configuración

**Solución**:
1. Copia todas las variables de entorno del servicio web al worker
2. Especialmente: `DATABASE_URL`, `SECRET_KEY`, `FLASK_ENV`

### Worker no procesa tareas

**Causa**: Worker no está conectado correctamente a Redis o no recibe tareas

**Solución**:
1. Verifica logs del worker: deberías ver `celery@hostname ready`
2. Verifica logs del servicio web: deberías ver `Email task enqueued`
3. Verifica que ambos servicios usen el mismo Redis (mismo `REDIS_URL`)

## Verificación rápida

Después de configurar, verifica en los logs del worker:

```
✅ REDIS_URL is set: redis://...
✅ Flask app created successfully
✅ Starting Celery worker...
celery@hostname ready
```

Si ves estos mensajes, el worker está configurado correctamente.

