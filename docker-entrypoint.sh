#!/bin/sh
set -eu

PUID="${PUID:-${UID:-1000}}"
PGID="${PGID:-${GID:-1000}}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-8000}"

run_as_app() {
  if [ "$(id -u)" = "0" ]; then
    gosu "${PUID}:${PGID}" "$@"
  else
    "$@"
  fi
}

if [ "$(id -u)" = "0" ]; then
  mkdir -p /app/staticfiles
  mkdir -p /app/media

  # Keep /app paths owned by the app uid/gid.
  chown -R "${PUID}:${PGID}" /app || true
fi

# Wait for PostgreSQL and apply migrations before starting Django.
until run_as_app python manage.py migrate --noinput; do
  echo "waiting for db..."
  sleep 2
done

if [ "$#" -eq 0 ]; then
  set -- python manage.py runserver "${WEB_HOST}:${WEB_PORT}"
fi

if [ "$(id -u)" = "0" ]; then
  exec gosu "${PUID}:${PGID}" "$@"
else
  exec "$@"
fi
