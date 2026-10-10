#!/bin/sh
# Container entrypoint: apply migrations, seed demo data (idempotent), serve.
set -e
alembic upgrade head
if [ "${SEED_DEMO_DATA:-true}" = "true" ]; then
  python -m scripts.seed
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*' --no-access-log
