# 🐳 Docker Setup para Desarrollo Local

Este proyecto usa Docker Compose para ejecutar PostgreSQL con PostGIS en desarrollo local.

## Requisitos

- Docker Desktop instalado y ejecutándose
- Docker Compose (incluido en Docker Desktop)

## Iniciar PostgreSQL

```bash
# Iniciar el contenedor de PostgreSQL
docker-compose up -d

# Ver logs
docker-compose logs -f postgres

# Detener el contenedor
docker-compose down

# Detener y eliminar volúmenes (⚠️ elimina todos los datos)
docker-compose down -v
```

## Configuración

El contenedor PostgreSQL está configurado con:

- **Usuario**: `tarracograf`
- **Contraseña**: `tarracograf_dev`
- **Base de datos**: `tarracograf`
- **Puerto**: `5432`
- **PostGIS**: Incluido (versión 3.4)

## Variables de Entorno

Añade estas variables a tu archivo `.env`:

```bash
# PostgreSQL Local (Docker)
SQLALCHEMY_DATABASE_URI=postgresql://tarracograf:tarracograf_dev@localhost:5432/tarracograf
```

## Verificar PostGIS

Una vez iniciado el contenedor, puedes verificar que PostGIS está disponible:

```bash
# Conectarse al contenedor
docker exec -it tarracograf_postgres psql -U tarracograf -d tarracograf

# En psql, ejecutar:
SELECT PostGIS_version();
```

O desde Python:

```python
from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    result = db.session.execute(db.text("SELECT PostGIS_version();"))
    print(result.scalar())
```

## Migraciones

Después de iniciar PostgreSQL, ejecuta las migraciones:

```bash
uv run flask db upgrade
```

## Importar Zonas

Una vez configurado PostgreSQL, puedes importar las zonas:

```bash
uv run python import_geojson_zones.py
```

## Solución de Problemas

### El contenedor no inicia

```bash
# Ver logs
docker-compose logs postgres

# Reiniciar
docker-compose restart postgres
```

### Puerto 5432 ya en uso

Si ya tienes PostgreSQL corriendo en el puerto 5432, puedes cambiar el puerto en `docker-compose.yml`:

```yaml
ports:
  - "5433:5432"  # Cambiar 5433 por el puerto que prefieras
```

Y actualizar la URI en `.env`:

```bash
SQLALCHEMY_DATABASE_URI=postgresql://tarracograf:tarracograf_dev@localhost:5433/tarracograf
```

### Limpiar todo y empezar de nuevo

```bash
# Detener y eliminar contenedores y volúmenes
docker-compose down -v

# Volver a iniciar
docker-compose up -d
```

