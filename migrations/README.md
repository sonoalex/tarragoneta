# Migraciones de Base de Datos

Este directorio contiene las migraciones de Alembic para la base de datos.

## Orden de las Migraciones

Las migraciones están ordenadas por la cadena de `down_revision` y tienen timestamps en el nombre del archivo para facilitar la visualización del orden cronológico.

1. **20251106_130612_6a9481a976b8** - `add_slug_field_to_initiatives.py` (base)
   - Fecha: 2025-11-06 13:06:12
   - Añade campo `slug` a la tabla `initiative`
   - Revision ID: `6a9481a976b8`

2. **20251107_010151_aa2d24bcfc2b** - `add_inventory_items_table.py`
   - Fecha: 2025-11-07 01:01:51
   - Crea la tabla `inventory_item`
   - Revision ID: `aa2d24bcfc2b`
   - Revises: `6a9481a976b8`

3. **20251107_011419_4908fda2abca** - `add_inventory_votes_and_importance_count.py`
   - Fecha: 2025-11-07 01:14:19
   - Añade tabla `inventory_vote` y campo `importance_count` a `inventory_item`
   - Revision ID: `4908fda2abca`
   - Revises: `aa2d24bcfc2b`

4. **20251110_113422_8eac5677c563** - `add_subcategory_field_to_inventoryitem.py` (head)
   - Fecha: 2025-11-10 11:34:22
   - Añade campo `subcategory` a `inventory_item`
   - Migra datos existentes a estructura jerárquica (category->subcategory)
   - Compatible con PostgreSQL (producción) y SQLite (desarrollo)
   - Revision ID: `8eac5677c563`
   - Revises: `4908fda2abca`

## Verificar el Orden

Para ver el historial de migraciones:

```bash
uv run flask db history
```

## Aplicar Migraciones

### Desarrollo Local
```bash
uv run flask db upgrade
```

### Producción (Railway)
Las migraciones se aplican automáticamente en el `release` phase del `Procfile`:
```
release: python compile_translations.py && flask db upgrade || python init_db.py || true
```

## Notas Importantes

- **PostgreSQL en Producción**: Las migraciones están optimizadas para PostgreSQL
- **SQLite en Desarrollo**: Compatible pero con limitaciones (ej: no se puede cambiar NOT NULL después de crear la columna)
- **Fallback**: Si las migraciones fallan, `init_db.py` intentará crear la columna `subcategory` manualmente

## Crear Nueva Migración

```bash
uv run flask db migrate -m "Descripción de la migración"
```

La nueva migración se creará automáticamente con el siguiente `down_revision` apuntando a la migración actual (head).

