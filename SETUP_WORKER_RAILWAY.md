# Configuración del Worker en Railway

Si el build del worker se congela, sigue estos pasos:

## Solución Rápida: Configurar Start Command Directamente

1. **Cancela el build congelado**:
   - En Railway, ve al servicio `worker`
   - Haz clic en "Cancel" o "Stop" si está disponible

2. **Configura el Start Command directamente**:
   - Ve a Settings → Deploy
   - En "Start Command", escribe:
     ```
     python worker.py
     ```
   - Esto sobrescribe el `railway.json` y evita usar `start_production.sh`

3. **Verifica las variables de entorno**:
   - Asegúrate de que el servicio `worker` tenga acceso a:
     - `REDIS_URL` (compartir desde el servicio web)
     - `DATABASE_URL` (si el worker necesita BD)
     - `MAIL_*` (para enviar emails)
     - `SERVER_NAME` o `RAILWAY_PUBLIC_DOMAIN` (para URLs en emails)
     - Otras variables necesarias

4. **Despliega manualmente**:
   - Haz clic en "Deploy" o espera a que Railway detecte el cambio

## Alternativa: Usar Variable de Entorno

Si prefieres usar `start_production.sh`, añade esta variable de entorno al servicio `worker`:

- Variable: `RUN_WORKER`
- Valor: `1`

Esto hará que `start_production.sh` detecte que es un worker y ejecute `python worker.py`.

## Verificar que Funciona

Una vez desplegado, revisa los logs del servicio `worker`. Deberías ver:

```
🚀 Starting RQ worker for email queue...
📧 Listening on queue: emails
🔗 Redis: ...
```

Si ves errores, verifica:
- Que Redis esté corriendo y accesible
- Que `REDIS_URL` esté configurada correctamente
- Que todas las dependencias estén instaladas

