#!/bin/sh
set -e

echo "Running database initialization..."
python init_db.py

echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"