#!/bin/bash

# Script para activar el webhook de Stripe en local usando Stripe CLI
# 
# Requisitos:
# 1. Instalar Stripe CLI: https://stripe.com/docs/stripe-cli
# 2. Autenticarse: stripe login
# 3. Tener Flask corriendo en http://localhost:5000

echo "🔗 Iniciando túnel de Stripe CLI para webhooks locales..."
echo ""
echo "📝 Asegúrate de que:"
echo "   1. Flask está corriendo en http://localhost:5000"
echo "   2. Has hecho 'stripe login'"
echo ""
echo "🌐 El webhook estará disponible en: https://[url-generada-por-stripe]"
echo ""

# Forward webhooks to local Flask app
# -f: forward to localhost:5000
# --events: solo los eventos que necesitamos
stripe listen \
  --forward-to localhost:5000/donate/webhook \
  --events checkout.session.completed,payment_intent.succeeded,charge.refunded

