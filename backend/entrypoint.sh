#!/bin/sh
set -e

echo "Attente de la base de données PostgreSQL..."
until python -c "
import sys, os
try:
    import psycopg
    url = os.environ['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://')
    conn = psycopg.connect(url)
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
