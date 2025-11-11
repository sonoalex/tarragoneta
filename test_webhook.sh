#!/bin/bash
# Script para verificar que el webhook funciona correctamente

echo "🔍 Verificando configuración del webhook..."
echo ""

# Verificar que el túnel está corriendo
if pgrep -f "stripe listen" > /dev/null; then
    echo "✅ Túnel de Stripe CLI está corriendo"
    echo "   PID: $(pgrep -f 'stripe listen' | head -1)"
else
    echo "❌ Túnel de Stripe CLI NO está corriendo"
    echo "   Ejecuta: ./stripe_webhook_local.sh"
    exit 1
fi

# Verificar que Flask está corriendo
if lsof -ti:5000 > /dev/null; then
    echo "✅ Flask está corriendo en puerto 5000"
else
    echo "❌ Flask NO está corriendo en puerto 5000"
    echo "   Ejecuta: ./start.sh"
    exit 1
fi

# Verificar webhook secret
if [ -f .env ] && grep -q "STRIPE_WEBHOOK_SECRET=" .env; then
    SECRET=$(grep "STRIPE_WEBHOOK_SECRET=" .env | cut -d'=' -f2)
    if [[ $SECRET == whsec_* ]]; then
        echo "✅ Webhook secret configurado: ${SECRET:0:20}..."
    else
        echo "⚠️  Webhook secret no tiene formato correcto (debe empezar con whsec_)"
    fi
else
    echo "❌ Webhook secret NO está configurado en .env"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🧪 Probando webhook con evento de prueba..."
echo ""

# Enviar evento de prueba
stripe trigger checkout.session.completed 2>&1 | grep -E "(Trigger|succeeded|failed)" | head -3

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Para recibir eventos REALES de pagos:"
echo ""
echo "   1. Asegúrate de que el túnel está corriendo: ./stripe_webhook_local.sh"
echo "   2. El túnel debe estar activo ANTES de hacer el pago"
echo "   3. Los eventos se capturan automáticamente cuando completas un pago"
echo "   4. Verifica los logs del túnel para ver los eventos entrantes"
echo ""
echo "💡 Tip: Los eventos reales aparecen en el túnel cuando completas"
echo "   un pago en la página de donación (http://localhost:5000/donate)"
echo ""

