#!/bin/bash

# Script para activar el webhook de Stripe en local usando Stripe CLI
# 
# Requisitos:
# 1. Instalar Stripe CLI: https://stripe.com/docs/stripe-cli
# 2. Autenticarse: stripe login
# 3. Tener Flask corriendo en http://localhost:5000

# Detener cualquier túnel anterior
pkill -f "stripe listen" 2>/dev/null
sleep 1

echo "🔗 Iniciando túnel de Stripe CLI para webhooks locales..."
echo ""
echo "📝 Asegúrate de que:"
echo "   1. Flask está corriendo en http://localhost:5000"
echo "   2. Has hecho 'stripe login'"
echo ""
echo "🌐 Los eventos se reenviarán a: http://localhost:5000/donate/webhook"
echo ""
echo "💡 Para probar, ejecuta en otra terminal:"
echo "   stripe trigger checkout.session.completed"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  Este proceso debe seguir corriendo para recibir eventos."
echo "   Presiona Ctrl+C para detenerlo."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Forward webhooks to local Flask app
# --events: solo los eventos que necesitamos
# --print-secret: muestra el secret al inicio
# Este comando se quedará corriendo hasta que lo detengas con Ctrl+C
stripe listen \
  --forward-to localhost:5000/donate/webhook \
  --events checkout.session.completed,payment_intent.succeeded,charge.refunded \
  --print-secret

