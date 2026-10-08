#!/bin/sh
set -eu

# Initialise the mounted data directories, never a database baked into the image.
if [ "${1:-}" = "gunicorn" ]; then
    : "${SECRET_KEY:?Set SECRET_KEY to a unique random value before starting IOE}"
    if [ "$SECRET_KEY" = "replace-with-a-unique-random-secret" ]; then
        echo "Replace the example SECRET_KEY before starting IOE." >&2
        exit 1
    fi
    mkdir -p /app/db /app/media /app/staticfiles /app/logs /app/backups /app/temp
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
