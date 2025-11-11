#!/bin/bash
# Script para configurar el webhook de Stripe y obtener el secret

echo "🔗 Configurando webhook de Stripe..."
echo ""

# Verificar que Stripe CLI está instalado
if ! command -v stripe &> /dev/null; then
    echo "❌ Stripe CLI no está instalado."
    echo "   Instálalo con: brew install stripe/stripe-cli/stripe"
    exit 1
fi

# Verificar autenticación
echo "✓ Verificando autenticación con Stripe..."
if ! stripe config --list &> /dev/null; then
    echo "⚠️  No estás autenticado con Stripe CLI"
    echo "   Ejecuta: stripe login"
    exit 1
fi

echo "✓ Autenticado con Stripe"
echo ""
echo "📝 Iniciando túnel de webhooks..."
echo "   Buscando el webhook secret..."
echo ""

# Crear un archivo temporal para capturar el output
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# Ejecutar stripe listen en background y capturar output
stripe listen \
  --forward-to localhost:5000/donate/webhook \
  --events checkout.session.completed,payment_intent.succeeded,charge.refunded \
  > "$TEMP_FILE" 2>&1 &
STRIPE_PID=$!

# Esperar a que aparezca el secret (máximo 10 segundos)
SECRET_FOUND=false
for i in {1..20}; do
    sleep 0.5
    if grep -q "whsec_" "$TEMP_FILE"; then
        WEBHOOK_SECRET=$(grep -o 'whsec_[a-zA-Z0-9]*' "$TEMP_FILE" | head -1)
        if [ -n "$WEBHOOK_SECRET" ]; then
            SECRET_FOUND=true
            break
        fi
    fi
done

# Matar el proceso de stripe listen
kill $STRIPE_PID 2>/dev/null
wait $STRIPE_PID 2>/dev/null

if [ "$SECRET_FOUND" = true ]; then
    echo ""
    echo "✅ Webhook secret encontrado: $WEBHOOK_SECRET"
    echo ""
    
    # Intentar añadirlo automáticamente si existe .env
    if [ -f .env ]; then
        # Verificar si ya existe
        if grep -q "^STRIPE_WEBHOOK_SECRET=" .env; then
            # Actualizar el valor existente
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                sed -i '' "s|^STRIPE_WEBHOOK_SECRET=.*|STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET|" .env
            else
                # Linux
                sed -i "s|^STRIPE_WEBHOOK_SECRET=.*|STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET|" .env
            fi
            echo "✓ Actualizado STRIPE_WEBHOOK_SECRET en .env"
        else
            echo "STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET" >> .env
            echo "✓ Añadido STRIPE_WEBHOOK_SECRET a .env"
        fi
    else
        echo "⚠️  Archivo .env no encontrado."
        echo "   Crea uno basado en env.example y añade:"
        echo "   STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET"
    fi
    
    echo ""
    echo "🚀 Ahora puedes iniciar el túnel de webhooks con:"
    echo "   ./stripe_webhook_local.sh"
    echo ""
    echo "   O manualmente:"
    echo "   stripe listen --forward-to localhost:5000/donate/webhook \\"
    echo "     --events checkout.session.completed,payment_intent.succeeded,charge.refunded"
else
    echo "⚠️  No se pudo capturar el webhook secret automáticamente."
    echo ""
    echo "   Ejecuta manualmente:"
    echo "   stripe listen --forward-to localhost:5000/donate/webhook \\"
    echo "     --events checkout.session.completed,payment_intent.succeeded,charge.refunded"
    echo ""
    echo "   Y copia el secret que empieza con 'whsec_' a tu archivo .env"
fi

