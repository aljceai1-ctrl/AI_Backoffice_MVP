#!/bin/bash
set -e

echo "==> Running migrations..."
python scripts/run_migrations.py

# Seed is optional and must never crash the container.
# Set SEED_DEMO_DATA=false to skip entirely.
if [ "${SEED_DEMO_DATA:-true}" = "true" ]; then
  echo "==> Seeding demo data..."
  python scripts/seed.py || echo "⚠ Seed failed (non-fatal) — continuing startup."
else
  echo "==> Skipping seed (SEED_DEMO_DATA=${SEED_DEMO_DATA})"
fi

echo "==> Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
