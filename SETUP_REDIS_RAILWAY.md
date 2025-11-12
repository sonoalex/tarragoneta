# Configuración de Redis para Colas de Email en Railway

Este documento explica cómo configurar Redis en Railway para que las colas de email funcionen correctamente.

## 🎯 ¿Por qué Redis?

El envío de emails puede tardar varios segundos, lo que genera una mala experiencia de usuario. Con Redis + RQ, los emails se envían en segundo plano, permitiendo que la aplicación responda inmediatamente.

## 📋 Pasos para Configurar Redis en Railway

### Opción 1: Añadir Redis como Servicio en Railway (Recomendado)

1. **Ve a tu proyecto en Railway**: https://railway.app
2. **Añade un nuevo servicio**:
   - Haz clic en "New" → "Database" → "Add Redis"
   - Railway creará automáticamente un servicio Redis
3. **Conecta el servicio Redis a tu aplicación**:
   - Railway automáticamente añadirá la variable de entorno `REDIS_URL` a tu servicio web
   - No necesitas hacer nada más, Railway lo detecta automáticamente

### Opción 2: Usar Redis Cloud (Alternativa)

Si prefieres usar un servicio externo:

1. **Crea una cuenta en Redis Cloud**: https://redis.com/try-free/
2. **Crea una base de datos Redis**
3. **Copia la URL de conexión** (formato: `redis://:password@host:port`)
4. **Añade la variable de entorno en Railway**:
   - Ve a tu servicio web en Railway
   - Settings → Variables
   - Añade: `REDISCLOUD_URL` = `tu-url-de-redis-cloud`

## ✅ Verificación

Una vez configurado, tu aplicación:

1. **Detectará automáticamente Redis** al iniciar
2. **Encolará emails** en lugar de enviarlos inmediatamente
3. **El worker procesará los emails** en segundo plano

### Verificar que funciona:

1. **Revisa los logs de la aplicación**:
   - Deberías ver: `Redis and email queue initialized successfully`
   - Al enviar un email: `Email queued for user@example.com: Subject (Job ID: xxx)`

2. **Revisa los logs del worker**:
   - Deberías ver: `🚀 Starting RQ worker for email queue...`
   - Cuando procesa un email: `Email sent successfully to user@example.com: Subject`

## 🔧 Configuración Local (Desarrollo)

Para desarrollo local, puedes:

1. **Instalar Redis localmente**:
   ```bash
   # macOS
   brew install redis
   brew services start redis
   
   # Linux
   sudo apt-get install redis-server
   sudo systemctl start redis
   ```

2. **O usar Docker**:
   ```bash
   docker run -d -p 6379:6379 redis:latest
   ```

3. **Configurar en `.env`**:
   ```bash
   REDIS_URL=redis://localhost:6379/0
   USE_EMAIL_QUEUE=True
   ```

## ⚙️ Variables de Entorno

- `REDIS_URL`: URL de conexión a Redis (Railway la proporciona automáticamente)
- `REDISCLOUD_URL`: URL alternativa de Redis Cloud
- `USE_EMAIL_QUEUE`: `True` para usar colas, `False` para envío síncrono (por defecto: `True`)

## 🚨 Troubleshooting

### Error: "Redis not available, emails will be sent synchronously"

**Causa**: Redis no está configurado o no es accesible.

**Solución**:
1. Verifica que el servicio Redis esté corriendo en Railway
2. Verifica que `REDIS_URL` esté configurada en las variables de entorno
3. Revisa los logs para ver el error específico

### Error: "Failed to queue email, sending synchronously"

**Causa**: La cola falló pero la aplicación hace fallback a envío síncrono.

**Solución**:
1. Verifica la conexión a Redis
2. Revisa los logs para ver el error específico
3. Asegúrate de que el worker esté corriendo

### Los emails no se envían

**Causa**: El worker no está corriendo.

**Solución**:
1. Verifica que el proceso `worker` esté activo en Railway
2. En Railway, deberías ver dos servicios:
   - `web`: Tu aplicación Flask
   - `worker`: El procesador de colas
3. Si no ves el worker, verifica el `Procfile`:
   ```
   worker: python worker.py
   ```

## 📊 Monitoreo

Puedes monitorear la cola usando:

1. **Logs de Railway**: Revisa los logs del worker para ver qué emails se están procesando
2. **RQ Dashboard** (opcional): Puedes añadir un dashboard web para monitorear la cola (requiere configuración adicional)

## 💡 Notas

- Si Redis no está disponible, la aplicación automáticamente enviará emails de forma síncrona (como antes)
- El worker debe estar corriendo para procesar los emails encolados
- Los emails se procesan en orden (FIFO: First In, First Out)
- Cada email tiene un timeout de 5 minutos

