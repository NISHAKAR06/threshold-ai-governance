#!/usr/bin/env bash
set -euo pipefail

# Simple helper to run Alembic migrations against the DATABASE_URL.
# Usage (Render Console):
#   bash scripts/run_migrations.sh
# If running locally, ensure DATABASE_URL is exported first.

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set. Export it first, e.g."
  echo "  export DATABASE_URL='postgres://user:pass@host:port/db'"
  exit 1
fi

echo "Using DATABASE_URL: ${DATABASE_URL}"

# Ensure alembic is available; install if missing
if ! command -v alembic >/dev/null 2>&1; then
  echo "alembic not found, installing..."
  pip install alembic >/dev/null
fi

echo "Running migrations..."
python -m alembic upgrade head
echo "Migrations complete."
