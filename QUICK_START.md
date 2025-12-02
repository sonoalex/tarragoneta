# ⚡ Inicio Rápido - Desarrollo Local

## 🚀 Pasos Rápidos

### 1. Configurar variables de entorno

```bash
# Si no tienes .env, cópialo desde el ejemplo
cp env.example .env

# Edita .env y configura:
# - MAIL_PASSWORD=tu-contraseña-de-email
# - ADMIN_PASSWORD=admin123 (o el que prefieras)
```

### 2. Probar configuración de email

```bash
python test_email_config.py
```

Deberías ver: ✅ Test email sent successfully

### 3. Iniciar aplicación

```bash
./start.sh
```

## ✅ Configuración Lista

La aplicación está configurada para desarrollo local con:

- ✅ **Email Provider**: SMTP (Hostinger)
- ✅ **Servidor SMTP**: `smtp.hostinger.com:465` (SSL)
- ✅ **Email por defecto**: `hola@tarracograf.cat`
- ✅ **Base de datos**: PostgreSQL con PostGIS (Docker)
- ✅ **Modo**: Development (DEBUG=True)

## 🔑 Acceso

- **URL**: http://127.0.0.1:5000
- **Admin Email**: `hola@tarracograf.cat`
- **Admin Password**: `admin123` (configurado en `.env`)

## 📚 Documentación Completa

- [Configuración Local Detallada](./SETUP_LOCAL.md)
- [Configuración SMTP Hostinger](./SETUP_HOSTINGER_SMTP.md)

