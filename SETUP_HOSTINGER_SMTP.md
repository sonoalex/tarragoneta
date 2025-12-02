# 📧 Configuración SMTP con Hostinger

Este documento explica cómo configurar Hostinger para enviar emails desde Tarracograf.

## 🔧 Configuración SMTP de Hostinger

Hostinger ofrece dos opciones para enviar emails:

### Opción 1: SSL (Recomendado) - Puerto 465
- **Servidor SMTP**: `smtp.hostinger.com`
- **Puerto**: `465`
- **Cifrado**: SSL
- **MAIL_USE_SSL**: `True`
- **MAIL_USE_TLS**: `False`

### Opción 2: TLS - Puerto 587
- **Servidor SMTP**: `smtp.hostinger.com`
- **Puerto**: `587`
- **Cifrado**: TLS/STARTTLS
- **MAIL_USE_SSL**: `False`
- **MAIL_USE_TLS**: `True`

## 📝 Variables de Entorno

Agrega estas variables a tu archivo `.env`:

```bash
# SMTP Configuration (Hostinger)
# Opción 1: SSL (recomendado) - Puerto 465
MAIL_SERVER=smtp.hostinger.com
MAIL_PORT=465
MAIL_USE_TLS=False
MAIL_USE_SSL=True

# Opción 2: TLS - Puerto 587 (si SSL no funciona)
# MAIL_SERVER=smtp.hostinger.com
# MAIL_PORT=587
# MAIL_USE_TLS=True
# MAIL_USE_SSL=False

MAIL_USERNAME=hola@tarracograf.cat
MAIL_PASSWORD=tu-contraseña-de-email
MAIL_DEFAULT_SENDER=Tarracograf <hola@tarracograf.cat>
MAIL_SUPPRESS_SEND=False
```

## 🔑 Credenciales

1. **MAIL_USERNAME**: Tu dirección de email completa (ej: `hola@tarracograf.cat`)
2. **MAIL_PASSWORD**: La contraseña de tu cuenta de email en Hostinger
   - Si has olvidado tu contraseña, puedes restablecerla desde el panel de control de Hostinger

## ✅ Verificación

1. Asegúrate de que tu cuenta de email esté creada en el panel de Hostinger
2. Verifica que la contraseña sea correcta
3. Prueba enviando un email de prueba desde la aplicación

## 🐛 Solución de Problemas

### Error de conexión
- Verifica que el puerto no esté bloqueado por tu firewall
- Prueba primero con SSL (puerto 465), luego con TLS (puerto 587)

### Error de autenticación
- Verifica que el email y contraseña sean correctos
- Asegúrate de usar la contraseña de la cuenta de email, no la del panel de Hostinger

### Error de dominio
- Verifica que el dominio `tarracograf.cat` esté correctamente configurado en Hostinger
- Asegúrate de que el email `hola@tarracograf.cat` exista

## 📚 Referencias

- [Hostinger Email Configuration](https://www.hostinger.com/support/1575756-how-to-get-email-account-configuration-details-for-hostinger-email)
- Para obtener más detalles, consulta la sección "Connect Apps & Devices" en el panel de control de Hostinger

