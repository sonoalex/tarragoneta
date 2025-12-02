# Configurar Gmail para Envío de Emails

Este documento explica cómo configurar Gmail para enviar emails desde Tarracograf.

## ⚠️ Error 535: Username and Password not accepted

Si ves este error, significa que las credenciales de Gmail no son válidas. Sigue estos pasos:

## 📋 Pasos para Configurar Gmail

### 1. Habilitar Verificación en 2 Pasos

**IMPORTANTE**: Debes tener la verificación en 2 pasos activada para poder generar App Passwords.

1. Ve a tu cuenta de Google: https://myaccount.google.com/
2. Ve a **Seguridad**
3. Busca **Verificación en 2 pasos**
4. Si no está activada, actívala siguiendo las instrucciones

### 2. Generar App Password

1. Ve a: https://myaccount.google.com/apppasswords
   - O desde Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones
2. Selecciona:
   - **Aplicación**: "Correo"
   - **Dispositivo**: "Otro (nombre personalizado)" → Escribe "Tarracograf"
3. Haz clic en **Generar**
4. **Copia la contraseña de 16 caracteres** que aparece (sin espacios)
   - Ejemplo: `abcd efgh ijkl mnop` → `abcdefghijklmnop`

### 3. Configurar en .env

Añade o actualiza estas líneas en tu archivo `.env`:

```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=hola@tarracograf.cat
MAIL_PASSWORD=abcdefghijklmnop  # ← Pega aquí la App Password de 16 caracteres
MAIL_DEFAULT_SENDER=Tarracograf <hola@tarracograf.cat>
MAIL_SUPPRESS_SEND=False
```

**⚠️ IMPORTANTE:**
- Usa la **App Password** (16 caracteres), NO tu contraseña normal de Gmail
- No incluyas espacios en la App Password
- La App Password es diferente a tu contraseña de Gmail

### 4. Verificar Configuración

1. Reinicia Flask para que cargue las nuevas variables
2. Prueba enviando un formulario de contacto
3. Revisa los logs para ver si hay errores

## 🔍 Troubleshooting

### Error: "Username and Password not accepted"

**Causas posibles:**
1. ❌ Estás usando tu contraseña normal en lugar de App Password
2. ❌ La App Password tiene espacios (quítalos)
3. ❌ La verificación en 2 pasos no está activada
4. ❌ La App Password fue revocada o eliminada

**Solución:**
1. Genera una nueva App Password
2. Asegúrate de copiarla sin espacios
3. Actualiza `MAIL_PASSWORD` en `.env`
4. Reinicia Flask

### Error: "Less secure app access"

Si ves este error, significa que estás intentando usar tu contraseña normal. **Debes usar App Password**, no tu contraseña de Gmail.

### No se envían emails pero no hay error

1. Verifica que `MAIL_SUPPRESS_SEND=False` en `.env`
2. Revisa los logs de Flask para ver si hay errores silenciosos
3. Verifica que el email de destino es válido

## 🧪 Probar en Desarrollo

Para no enviar emails reales durante el desarrollo, puedes configurar:

```bash
MAIL_SUPPRESS_SEND=True
```

Esto hará que los emails se logueen pero no se envíen realmente.

## 📧 Configuración en Producción (Railway)

En Railway, añade estas variables de entorno:

1. Ve a tu proyecto en Railway
2. **Variables** → **Add Variable**
3. Añade todas las variables de mail:
   - `MAIL_SERVER=smtp.gmail.com`
   - `MAIL_PORT=587`
   - `MAIL_USE_TLS=True`
   - `MAIL_USE_SSL=False`
   - `MAIL_USERNAME=hola@tarracograf.cat`
   - `MAIL_PASSWORD=tu-app-password-de-16-caracteres`
   - `MAIL_DEFAULT_SENDER=Tarracograf <hola@tarracograf.cat>`
   - `MAIL_SUPPRESS_SEND=False`
   - `ADMIN_EMAIL=hola@tarracograf.cat` (opcional)

## 🔐 Seguridad

- **NUNCA** commitees el archivo `.env` con contraseñas reales
- Usa App Passwords, no contraseñas normales
- Si una App Password se compromete, revócala y genera una nueva
- En producción, usa variables de entorno, no archivos `.env`

## 📝 Notas Adicionales

- Gmail tiene límites de envío: 500 emails/día para cuentas gratuitas
- Para más volumen, considera usar un servicio como SendGrid o Mailgun
- Las App Passwords son específicas por aplicación, puedes tener varias

