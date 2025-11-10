# Configurar Webhooks de Stripe en Desarrollo Local

## Pasos Rápidos

### 1. Instalar Stripe CLI

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Linux/Windows: https://stripe.com/docs/stripe-cli
```

### 2. Autenticarse

```bash
stripe login
```

### 3. Iniciar Flask

En una terminal:

```bash
uv run flask run
# O
./start.sh
```

### 4. Iniciar el túnel de webhooks

En otra terminal:

```bash
./stripe_webhook_local.sh
```

O manualmente:

```bash
stripe listen --forward-to localhost:5000/donate/webhook \
  --events checkout.session.completed,payment_intent.succeeded,charge.refunded
```

### 5. Copiar el Webhook Secret

Stripe CLI mostrará algo como:

```
> Ready! Your webhook signing secret is whsec_xxxxxxxxxxxxx
```

Copia ese secreto (empieza con `whsec_`) y añádelo a tu archivo `.env`:

```bash
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

### 6. Reiniciar Flask

Reinicia Flask para que cargue la nueva variable de entorno.

### 7. Probar

1. Ve a http://localhost:5000/donate
2. Haz una donación de prueba usando la tarjeta: `4242 4242 4242 4242`
3. Verifica en los logs de Stripe CLI que el webhook se recibió
4. Verifica en la base de datos:

```bash
sqlite3 tarragoneta.db "SELECT id, amount, email, status, created_at FROM donation ORDER BY created_at DESC LIMIT 5;"
```

## Verificar que funciona

### Logs de Stripe CLI

Deberías ver algo como:

```
2025-11-10 17:30:00  --> checkout.session.completed [evt_xxxxx]
2025-11-10 17:30:00  <-- [200] POST http://localhost:5000/donate/webhook [evt_xxxxx]
```

### Logs de Flask

Deberías ver:

```
INFO: Stripe webhook received: checkout.session.completed
INFO: Payment successful for session: cs_test_xxxxx, amount: 5.0€
INFO: Donation saved: 1 - 5.0€
```

### Base de datos

```bash
sqlite3 tarragoneta.db "SELECT * FROM donation;"
```

Deberías ver la donación con `status='completed'`.

## Troubleshooting

### El webhook no se recibe

1. Verifica que Flask está corriendo en `localhost:5000`
2. Verifica que el túnel de Stripe CLI está activo
3. Verifica que `STRIPE_WEBHOOK_SECRET` está en tu `.env`
4. Reinicia Flask después de añadir el secret

### Error "Webhook secret not configured"

Asegúrate de que `STRIPE_WEBHOOK_SECRET` está en tu `.env` y Flask se reinició.

### Error "Invalid signature"

El webhook secret no coincide. Asegúrate de usar el que Stripe CLI muestra (empieza con `whsec_`).

### La donación no se guarda

1. Revisa los logs de Flask para ver errores
2. Verifica que la tabla `donation` existe: `sqlite3 tarragoneta.db ".tables"`
3. Verifica que las migraciones están aplicadas: `uv run flask db current`

