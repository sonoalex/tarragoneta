# 🚀 Cómo Arrancar Tarragoneta

## Opción 1: Script Automático (Recomendado)

```bash
./start.sh
```

Este script hace todo automáticamente:
- Activa el entorno virtual
- Verifica dependencias
- Inicializa migraciones si es necesario
- Aplica migraciones
- Compila traducciones
- Verifica/crea usuario admin
- Arranca el servidor

## Opción 2: Manual

### 1. Activar entorno virtual
```bash
source .venv/bin/activate
```

### 2. Instalar dependencias (si es necesario)
```bash
uv pip install --python .venv/bin/python -r requirements.txt
```

### 3. Inicializar base de datos
```bash
flask init-db
```

Este comando:
- Aplica las migraciones
- Crea los roles (admin, user, moderator)
- Crea el usuario admin si no existe

### 4. Compilar traducciones
```bash
python compile_translations.py
```

### 5. Arrancar servidor
```bash
flask run
```

O con opciones:
```bash
flask run --host=0.0.0.0 --port=5000 --debug
```

## Credenciales por Defecto

- **Email**: `admin@tarragoneta.org`
- **Password**: `admin123` (solo desarrollo - **cambiar en producción**)

## Solución de Problemas

### Error: "no such column: initiative.slug"
```bash
flask db migrate -m "Add slug to initiatives"
flask db upgrade
```

### Error: "contraseña no válida"
```bash
python fix_admin.py
```

### Error: "bcrypt version"
```bash
uv pip install --python .venv/bin/python "bcrypt==3.2.2"
python fix_admin.py
```

### Reiniciar desde cero
```bash
rm instance/tarragoneta.db
rm -rf migrations/versions/*
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
flask init-db
```

