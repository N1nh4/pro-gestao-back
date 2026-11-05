#!/bin/sh
set -eu

if [ "${RUN_DB_INIT:-true}" = "true" ]; then
    echo "Inicializando banco de dados..."
    if [ "${SEED_DEMO:-false}" = "true" ]; then
        python -m app.db.seed --demo
    else
        python -m app.db.seed
    fi
fi

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-1}" \
    --proxy-headers \
    --forwarded-allow-ips="*"
