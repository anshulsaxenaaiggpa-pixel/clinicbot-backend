#!/bin/bash
# Railway startup script - runs migrations then starts the app

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Seeding test data..."
python seed_test_data.py

echo "==> Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
