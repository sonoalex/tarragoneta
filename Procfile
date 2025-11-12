release: export FLASK_APP=app.py && python compile_translations.py && flask db upgrade || python init_db.py || true
web: bash start_production.sh
worker: python worker.py

