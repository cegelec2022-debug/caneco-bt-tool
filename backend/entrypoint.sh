#!/bin/sh
set -e

echo "Attente de la base de données PostgreSQL..."
until python -c "
import sys, os
try:
    import psycopg
    conn = psycopg.connect(os.environ['DATABASE_URL'])
    conn.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  printf '.'
  sleep 2
done
echo ""
echo "Base de données disponible."

echo "Application des migrations Alembic..."
alembic upgrade head

echo "Démarrage du serveur FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
