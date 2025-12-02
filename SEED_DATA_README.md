# 📊 Scripts de Seed Data

Este proyecto tiene dos scripts para generar datos de ejemplo:

## `seed_data.py` - Datos de Inventario

**Propósito**: Genera items de inventario (palomas, basura, etc.) con datos realistas.

**Características**:
- ✅ Genera items con coordenadas reales de Tarragona
- ✅ Asigna automáticamente la sección administrativa basándose en coordenadas
- ✅ Descarga imágenes de ejemplo (opcional, 40% probabilidad)
- ✅ Distribuye items por categorías y estados de forma realista
- ✅ Evita duplicados en la misma ubicación

**Uso**:
```bash
# Generar 50 items (por defecto)
python seed_data.py

# Generar 100 items
python seed_data.py --count 100

# Limpiar items existentes y generar nuevos
python seed_data.py --clear --count 50
```

## `seed_all.py` - Orquestador Completo

**Propósito**: Script orquestador que genera todos los datos de ejemplo (usuarios, iniciativas, inventario).

**Características**:
- ✅ Crea usuarios de prueba con diferentes roles
- ✅ Genera iniciativas de ejemplo
- ✅ Genera datos de inventario (llama a `seed_data.py`)
- ✅ Opciones para generar solo una parte de los datos

**Uso**:
```bash
# Generar todos los datos
python seed_all.py

# Solo usuarios de prueba
python seed_all.py --users-only

# Solo iniciativas
python seed_all.py --initiatives-only

# Solo inventario
python seed_all.py --inventory-only --inventory-count 100

# Limpiar inventario antes de generar
python seed_all.py --inventory-only --clear-inventory

# Resetear toda la base de datos (⚠️ elimina todo)
python seed_all.py --reset-db
```

## Recomendación

- **Para desarrollo rápido**: Usa `seed_all.py` para generar todo
- **Para solo inventario**: Usa `seed_data.py` directamente
- **Para producción**: No uses estos scripts (solo para desarrollo)

## Asignación Automática de Secciones

Los items de inventario se asignan automáticamente a secciones administrativas basándose en sus coordenadas:

1. **PostGIS** (si está disponible): Usa consultas espaciales eficientes
2. **Shapely** (fallback): Verifica polígonos WKT manualmente

Si un item no puede asignarse a una sección, se crea sin `section_id` (nullable).

