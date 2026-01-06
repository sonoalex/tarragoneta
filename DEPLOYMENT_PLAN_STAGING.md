# Plan de Despliegue a Staging - Migración de Categorías

## 📋 Resumen
Este plan detalla los pasos necesarios para completar la migración del sistema de categorías de inventario de valores hardcoded a un sistema basado en base de datos, una vez desplegado el código en staging.

---

## ✅ Pre-requisitos
- [ ] Código desplegado en staging (rama `develop`)
- [ ] Acceso SSH a staging
- [ ] Acceso a la base de datos de staging
- [ ] Backup de la base de datos realizado

---

## 🔄 Paso 1: Ejecutar Script de Seed de Categorías

Este script crea las categorías y subcategorías en la base de datos con los nuevos códigos en catalán y los iconos de Font Awesome.

```bash
# Conectar a staging
ssh usuario@staging-server

# Activar entorno virtual
cd /ruta/a/tarragoneta
source .venv/bin/activate  # o el comando equivalente para tu entorno

# Ejecutar script de seed
python scripts/seed_categories.py
```

**Verificación esperada:**
- ✅ 8 categorías principales creadas/actualizadas
- ✅ 22+ subcategorías creadas/actualizadas
- ✅ Iconos actualizados a Font Awesome (fa-dove, fa-trash, etc.)

**Si hay errores:**
- Verificar que existe un usuario admin en la BD
- Verificar permisos de escritura en la BD
- Revisar logs del script

---

## 🔄 Paso 2: Ejecutar Script de Migración de Items

Este script crea las relaciones many-to-many entre `InventoryItem` y `InventoryCategory`.

```bash
# En el mismo entorno
python scripts/migrate_items_to_categories.py
```

**Verificación esperada:**
- ✅ Items migrados: X (número de items en staging)
- ✅ Items ya migrados (omitidos): 0 (primera vez)
- ✅ Errores: 0
- ✅ Items con categorías asociadas: X de X

**Si hay errores:**
- Revisar el mapeo de categorías en el script
- Verificar que todas las categorías existen en `InventoryCategory`
- Revisar logs del script

---

## ✅ Paso 3: Verificaciones Funcionales

### 3.1 Mapa de Inventario Principal
- [ ] Acceder a `/inventory`
- [ ] Verificar que se muestran 32 items (excluyendo container overflows)
- [ ] Verificar que el sidebar muestra "32 Items reportats"
- [ ] Verificar que las "Top categories" aparecen correctamente
- [ ] Probar filtros por categoría (coloms, contenidors, etc.)
- [ ] Probar filtros por subcategoría
- [ ] Verificar que los iconos son Font Awesome (no emojis)

### 3.2 Formulario de Reportar Item
- [ ] Acceder a `/inventory/report`
- [ ] Verificar que el dropdown de categorías carga desde BD
- [ ] Verificar que el dropdown de subcategorías se actualiza dinámicamente
- [ ] Crear un item de prueba y verificar que se guarda correctamente

### 3.3 Analytics
- [ ] Acceder a `/admin/analytics/trends`
- [ ] Verificar que los gráficos se muestran correctamente
- [ ] Verificar que los filtros funcionan
- [ ] Acceder a `/admin/analytics/inventory-by-zone`
- [ ] Verificar que muestra 32 items (no 38)
- [ ] Verificar que los contadores coinciden con el mapa principal

### 3.4 Gestión de Categorías (Admin)
- [ ] Acceder a `/admin/inventory/categories`
- [ ] Verificar que se listan todas las categorías principales
- [ ] Verificar que se muestran las subcategorías bajo cada categoría
- [ ] Probar crear una nueva categoría
- [ ] Probar editar una categoría existente
- [ ] Probar desactivar una categoría

### 3.5 Hero Page
- [ ] Acceder a `/` (página principal)
- [ ] Verificar que las categorías se muestran dinámicamente desde BD
- [ ] Verificar que los iconos son Font Awesome
- [ ] Verificar que los contadores son correctos

### 3.6 Container Points
- [ ] Verificar que el modo "Punts de contenidors" funciona
- [ ] Crear un punto de contenedor
- [ ] Reportar un desbordamiento en un punto existente
- [ ] Verificar que se actualiza en tiempo real en el mapa

---

## 🧹 Paso 4: Limpieza y Verificación Final

### 4.1 Verificar Consistencia de Datos
```sql
-- Verificar que todos los items tienen relaciones
SELECT COUNT(*) FROM inventory_item_categories;
-- Debe ser >= número de items

-- Verificar items sin categorías
SELECT i.id, i.category, i.subcategory 
FROM inventory_item i 
LEFT JOIN inventory_item_categories ic ON i.id = ic.item_id 
WHERE ic.item_id IS NULL;
-- Debe estar vacío o solo items muy antiguos sin categoría válida
```

### 4.2 Verificar que no hay items con subcategorías obsoletas
```sql
-- Verificar items con subcategorías de container overflow obsoletas
SELECT COUNT(*) FROM inventory_item 
WHERE category IN ('contenidors', 'basura') 
AND subcategory IN ('escombreries_desbordades', 'basura_desbordada', 'deixadesa');
-- Debe ser 0 o muy pocos (que se pueden limpiar manualmente)
```

### 4.3 Verificar Iconos en BD
```sql
-- Verificar que los iconos son Font Awesome
SELECT code, icon FROM inventory_category WHERE parent_id IS NULL;
-- Todos deben empezar con 'fa-' (ej: 'fa-dove', 'fa-trash')
```

---

## 📝 Paso 5: Documentación y Notas

### Notas Importantes:
1. **Código Legacy**: El código actual mantiene compatibilidad con códigos legacy (`palomas`, `basura`, etc.) para que funcione hasta que se ejecuten los scripts. Una vez ejecutados, el código seguirá funcionando pero ya no será necesario.

2. **Campos `category` y `subcategory`**: Estos campos en `InventoryItem` NO se actualizan en el script de migración. Se mantendrán con valores legacy hasta el último paso de limpieza (cuando eliminemos estos campos completamente).

3. **Container Overflow**: Los items con subcategorías `escombreries_desbordades`, `basura_desbordada`, `deixadesa` están excluidos del inventario principal porque ahora se manejan con Container Points.

4. **Iconos Font Awesome**: Todos los iconos de categorías ahora son clases de Font Awesome (ej: `fa-dove`, `fa-trash`) en lugar de emojis.

---

## 🚨 Troubleshooting

### Problema: Script de seed falla
- **Causa**: No hay usuario admin
- **Solución**: Crear un usuario admin primero o modificar el script para crear categorías sin `created_by_id`

### Problema: Items no se muestran en el mapa
- **Causa**: Filtro de container overflow muy restrictivo
- **Solución**: Verificar que los items no tienen subcategorías obsoletas

### Problema: Contadores no coinciden
- **Causa**: Items con códigos legacy no se están contando
- **Solución**: Verificar que el código de normalización funciona correctamente

### Problema: Iconos no se muestran
- **Causa**: Font Awesome no está cargado o iconos incorrectos en BD
- **Solución**: Verificar que Font Awesome está incluido en `base.html` y que los iconos en BD son correctos

---

## ✅ Checklist Final

- [ ] Script de seed ejecutado exitosamente
- [ ] Script de migración ejecutado exitosamente
- [ ] Todos los items tienen relaciones many-to-many
- [ ] Mapa de inventario muestra 32 items
- [ ] Filtros funcionan correctamente
- [ ] Analytics muestran datos correctos
- [ ] Gestión de categorías funciona
- [ ] Hero page muestra categorías dinámicas
- [ ] Iconos son Font Awesome
- [ ] Container points funcionan
- [ ] No hay errores en logs
- [ ] Backup de BD realizado antes de cambios

---

## 🎯 Siguiente Fase (Post-Staging)

Una vez verificado todo en staging:
1. Merge a `main` (producción)
2. Ejecutar los mismos scripts en producción
3. Verificaciones en producción
4. **Último paso**: Eliminar campos `category` y `subcategory` de `InventoryItem` y actualizar todo el código para usar solo relaciones many-to-many

---

**Fecha de creación**: $(date)
**Última actualización**: $(date)

