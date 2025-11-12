# Lista de Emails de Tarragoneta

Este documento lista todos los emails que se envían desde la plataforma Tarragoneta.

## 📧 Emails Implementados

### 1. **Email de Bienvenida** (`welcome.html`)
- **Cuándo se envía**: Al registrarse un nuevo usuario
- **Destinatario**: Usuario recién registrado
- **Contenido**: 
  - Mensaje de bienvenida
  - Información sobre qué puede hacer en la plataforma (incluyendo reportar el estado de la ciudad: palomas, basura, etc.)
  - Enlace para iniciar sesión

### 2. **Confirmación de Donación** (`donation_confirmation.html`)
- **Cuándo se envía**: Después de una donación exitosa
- **Destinatario**: Donante (usuario registrado o anónimo)
- **Contenido**:
  - Agradecimiento
  - Detalles de la donación (cantidad, fecha, estado)
  - Información sobre cómo se usa la donación (incluyendo mantener el inventario actualizado)
  - Enlace a la plataforma

### 3. **Iniciativa Aprobada** (`initiative_approved.html`)
- **Cuándo se envía**: Cuando un administrador aprueba una iniciativa
- **Destinatario**: Creador de la iniciativa
- **Contenido**:
  - Notificación de aprobación
  - Detalles de la iniciativa (título, fecha, ubicación)
  - Enlace a la iniciativa

### 4. **Iniciativa Rechazada** (`initiative_rejected.html`)
- **Cuándo se envía**: Cuando un administrador rechaza una iniciativa
- **Destinatario**: Creador de la iniciativa
- **Contenido**:
  - Notificación de rechazo
  - Motivo del rechazo (si se proporciona)
  - Enlace para contactar

### 5. **Recordatorio de Iniciativa** (`initiative_reminder.html`)
- **Cuándo se envía**: Un día antes de la fecha de la iniciativa
- **Destinatario**: Creador de la iniciativa
- **Contenido**:
  - Recordatorio de la fecha
  - Detalles de la iniciativa
  - Enlace a la iniciativa

### 6. **Confirmación de Participación** (`participant_confirmation.html`)
- **Cuándo se envía**: Cuando alguien se une a una iniciativa
- **Destinatario**: Participante (registrado o anónimo)
- **Contenido**:
  - Confirmación de participación
  - Detalles de la iniciativa
  - Enlace a la iniciativa

### 7. **Reportaje Aprobado** (`inventory_approved.html`)
- **Cuándo se envía**: Cuando un administrador aprueba un reportaje del inventario
- **Destinatario**: Usuario que reportó el item
- **Contenido**:
  - Notificación de aprobación
  - Detalles del reportaje
  - Enlace al mapa

### 8. **Reportaje Rechazado** (`inventory_rejected.html`)
- **Cuándo se envía**: Cuando un administrador rechaza un reportaje del inventario
- **Destinatario**: Usuario que reportó el item
- **Contenido**:
  - Notificación de rechazo
  - Motivo del rechazo (si se proporciona)
  - Enlace para contactar

### 9. **Respuesta al Formulario de Contacto** (`contact_response.html`)
- **Cuándo se envía**: Después de enviar el formulario de contacto
- **Destinatario**: Usuario que envió el formulario
- **Contenido**:
  - Confirmación de recepción
  - Información sobre el seguimiento
  - Enlace a la plataforma

### 10. **Notificación de Administrador** (`admin_notification.html`)
- **Cuándo se envía**: Para notificar a administradores sobre eventos importantes
- **Destinatario**: Administradores
- **Contenido**:
  - Tipo de notificación
  - Datos relevantes
  - Enlace al panel de administración

## 🔧 Configuración

### Variables de Entorno Necesarias

```bash
# Configuración de Gmail
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=hola@tarragoneta.com
MAIL_PASSWORD=tu-app-password-de-google
MAIL_DEFAULT_SENDER=Tarragoneta <hola@tarragoneta.com>

# Para desarrollo (no envía emails reales)
MAIL_SUPPRESS_SEND=True
```

### Configurar App Password de Google

1. Ve a tu cuenta de Google
2. Seguridad → Verificación en 2 pasos (debe estar activada)
3. Contraseñas de aplicaciones
4. Genera una nueva contraseña para "Correo"
5. Usa esa contraseña en `MAIL_PASSWORD`

## 📝 Uso del Servicio

```python
from app.services.email_service import EmailService

# Enviar email de bienvenida
EmailService.send_welcome_email(user)

# Enviar confirmación de donación
EmailService.send_donation_confirmation(donation, user)

# Enviar email personalizado
EmailService.send_email(
    to='usuario@example.com',
    subject='Asunto',
    template='mi_template',
    variable1='valor1',
    variable2='valor2'
)
```

## 🎨 Estilo de las Plantillas

Todas las plantillas usan:
- **Colores de la plataforma**: Verde (#4A9B5C), crema (#F5F5F0), amarillo (#FFD700)
- **Fuente**: Nunito (misma que la web)
- **Diseño responsive**: Compatible con móviles
- **Estilo consistente**: Mismo look & feel que la plataforma web
- **Información del inventario**: Todas las plantillas incluyen información sobre cómo reportar el estado actual de la ciudad (palomas: nidos, excrementos, plumas; basura: contenedores desbordados, vertidos; y más cosas en el futuro)

## 📋 Próximos Emails a Implementar

- [ ] Email de recuperación de contraseña (si se implementa)
- [ ] Email de cambio de contraseña
- [ ] Email de notificación de nuevos participantes en iniciativa
- [ ] Email semanal de resumen de actividades
- [ ] Email de agradecimiento por reportaje resuelto

