# Migraciones de Base de Datos

Este directorio contiene las migraciones de Alembic para la base de datos.

## Orden de las Migraciones

Las migraciones están ordenadas por la cadena de `down_revision`. El orden actual es:

1. **6a9481a976b8** - `add_slug_field_to_initiatives.py` (base)
   - Añade campo `slug` a la tabla `initiative`

2. **aa2d24bcfc2b** - `add_inventory_items_table.py`
   - Crea la tabla `inventory_item`
   - Revises: `6a9481a976b8`

3. **4908fda2abca** - `add_inventory_votes_and_importance_count.py`
   - Añade tabla `inventory_vote` y campo `importance_count` a `inventory_item`
   - Revises: `aa2d24bcfc2b`

4. **8eac5677c563** - `add_subcategory_field_to_inventoryitem.py` (head)
   - Añade campo `subcategory` a `inventory_item`
   - Migra datos existentes a estructura jerárquica (category->subcategory)
   - Compatible con PostgreSQL (producción) y SQLite (desarrollo)
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

