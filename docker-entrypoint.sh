#!/bin/sh
set -eu

# Runtime identity and bind address defaults can be overridden by the
# container environment.
PUID="${PUID:-${UID:-1000}}"
PGID="${PGID:-${GID:-1000}}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-8000}"
SQLITE_PATH="${SQLITE_PATH:-/data/db.sqlite3}"
export SQLITE_PATH

# Simple timestamped logger that writes to stderr.
log() {
  level="$1"; shift || true
  timestamp="$(TZ="${TZ:-UTC}" date +'%Y-%m-%dT%H:%M:%S%z' 2>/dev/null || date +'%Y-%m-%dT%H:%M:%S%z')"
  printf '%s %s: %s\n' "$timestamp" "$level" "$*" >&2
}

trap 'log "INFO" "Entrypoint exiting"; exit' INT TERM

# Run commands as the configured app user when the container starts as root.
run_as_app() {
  if [ "$(id -u)" = "0" ]; then
    gosu "${PUID}:${PGID}" "$@"
  else
    "$@"
  fi
}

if [ "$(id -u)" = "0" ]; then
  # Prepare writable Django static directories before dropping privileges.
  log "INFO" "Preparing /app directories"
  mkdir -p /app/static /app/staticfiles

  # Keep /app paths owned by the app uid/gid.
  chown -R "${PUID}:${PGID}" /app || true

  # When the SQLite database is stored outside /app (e.g. on a mounted
  # volume), make sure its directory exists and is writable by the app user.
  if [ -n "$SQLITE_PATH" ]; then
    SQLITE_DIR="$(dirname "${SQLITE_PATH}")"
    log "INFO" "Preparing database directory ${SQLITE_DIR}"
    mkdir -p "${SQLITE_DIR}"
    chown -R "${PUID}:${PGID}" "${SQLITE_DIR}" || true
  fi
fi

# Apply SQLite-backed migrations before starting Django.
run_as_app python manage.py migrate --noinput

log "INFO" "Running collectstatic"
run_as_app python manage.py collectstatic --noinput
log "INFO" "collectstatic finished"

# Standardmaessig laeuft der Produktiv-WSGI-Server (gunicorn); statische
# Dateien liefert Whitenoise aus dem Anwendungsprozess. Der Django-Devserver
# mit Auto-Reload laesst sich fuer die Entwicklung ueber USE_DEV_SERVER=1
# aktivieren (siehe compose.dev.yaml).
if [ "$#" -eq 0 ]; then
  if [ "${USE_DEV_SERVER:-0}" = "1" ]; then
    set -- python manage.py runserver "${WEB_HOST}:${WEB_PORT}"
  else
    set -- gunicorn config.wsgi:application \
      --bind "${WEB_HOST}:${WEB_PORT}" \
      --workers "${WEB_CONCURRENCY:-3}" \
      --access-logfile - \
      --error-logfile -
  fi
fi

if [ "$(id -u)" = "0" ]; then
  log "INFO" "Executing as ${PUID}:${PGID}: $*"
  exec gosu "${PUID}:${PGID}" "$@"
else
  log "INFO" "Executing: $*"
  exec "$@"
fi
