# Configurar Webhook de Stripe en Staging/Producción

En staging/producción, el webhook se configura directamente en el **Dashboard de Stripe**, no con Stripe CLI.

## Pasos para Configurar el Webhook en Stripe Dashboard

### 1. Acceder al Dashboard de Stripe

1. Ve a [https://dashboard.stripe.com](https://dashboard.stripe.com)
2. Inicia sesión con tu cuenta de Stripe
3. **Importante**: Asegúrate de estar en el modo correcto:
   - **Test mode** para staging/desarrollo
   - **Live mode** para producción

### 2. Crear el Webhook Endpoint

1. En el menú lateral, ve a **Developers** → **Webhooks**
2. Haz clic en **"Add endpoint"** o **"+ Add endpoint"**
3. Configura el endpoint:
   - **Endpoint URL**: `https://tu-dominio-staging.com/donate/webhook`
     - Ejemplo: `https://tarragoneta-staging.railway.app/donate/webhook`
     - Ejemplo: `https://tarragoneta.railway.app/donate/webhook` (producción)
   - **Description**: "Tarragoneta - Donations Webhook" (opcional)
   - **Events to send**: Selecciona los eventos específicos:
     - ✅ `checkout.session.completed`
     - ✅ `payment_intent.succeeded`
     - ✅ `charge.refunded`
     - ✅ `payment_intent.created` (opcional, para logging)
     - ✅ `charge.updated` (opcional, para logging)
     - ✅ `charge.succeeded` (opcional, para logging)

### 3. Obtener el Webhook Secret

Después de crear el endpoint:

1. Haz clic en el endpoint que acabas de crear
2. En la sección **"Signing secret"**, verás un secret que empieza con `whsec_`
3. Haz clic en **"Reveal"** o **"Click to reveal"** para ver el secret completo
4. **Copia el secret completo** (empieza con `whsec_`)

### 4. Configurar el Secret en Railway/Staging

1. Ve a tu proyecto en Railway
2. Ve a **Variables** → **Add Variable**
3. Añade la variable:
   - **Name**: `STRIPE_WEBHOOK_SECRET`
   - **Value**: El secret que copiaste (empieza con `whsec_`)
4. Guarda los cambios

### 5. Verificar la Configuración

1. En el Dashboard de Stripe, ve a tu webhook
2. Haz clic en **"Send test webhook"** o usa el botón de prueba
3. Selecciona el evento `checkout.session.completed`
4. Verifica que tu aplicación recibe el webhook correctamente

## URLs de Ejemplo

### Staging
```
https://tu-app-staging.railway.app/donate/webhook
```

### Producción
```
https://tu-app.railway.app/donate/webhook
```

## Eventos Recomendados

**Mínimos necesarios:**
- `checkout.session.completed` - Cuando se completa un pago
- `payment_intent.succeeded` - Confirmación adicional del pago
- `charge.refunded` - Cuando se reembolsa un pago

**Opcionales (para logging):**
- `payment_intent.created`
- `charge.succeeded`
- `charge.updated`

## Verificar que Funciona

1. Haz una donación de prueba desde tu aplicación en staging
2. Ve al Dashboard de Stripe → **Developers** → **Webhooks** → Tu endpoint
3. Deberías ver los eventos entrantes en la sección **"Recent events"**
4. Si hay errores, verás el código de estado (200 = éxito, otros = error)

## Troubleshooting

### Error 400: Invalid signature
- Verifica que el `STRIPE_WEBHOOK_SECRET` en Railway coincide con el del Dashboard
- Asegúrate de que estás usando el secret correcto (Test mode vs Live mode)

### Error 500: Internal server error
- Revisa los logs de Railway para ver el error específico
- Verifica que la base de datos está configurada correctamente
- Asegúrate de que todas las migraciones están aplicadas

### No se reciben eventos
- Verifica que la URL del webhook es correcta y accesible públicamente
- Asegúrate de que el endpoint está activo en el Dashboard de Stripe
- Verifica que los eventos están seleccionados correctamente

## Notas Importantes

⚠️ **Test Mode vs Live Mode:**
- Los webhooks de **Test mode** tienen un secret diferente a los de **Live mode**
- Asegúrate de usar el secret correcto según el modo en el que estés trabajando
- En staging, normalmente usarás **Test mode**
- En producción, usarás **Live mode**

⚠️ **Secrets Diferentes:**
- El webhook secret de desarrollo local (Stripe CLI) es diferente al de staging/producción
- Cada entorno necesita su propio secret configurado

⚠️ **HTTPS Requerido:**
- Stripe solo envía webhooks a URLs HTTPS
- Asegúrate de que tu aplicación en staging/producción tenga HTTPS habilitado

