#!/bin/sh
set -eu

# Runtime identity and bind address defaults can be overridden by the
# container environment.
PUID="${PUID:-${UID:-1000}}"
PGID="${PGID:-${GID:-1000}}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-8000}"

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
  mkdir -p /app/staticfiles
  mkdir -p /app/static/kern

  # The project requires the packaged KERN static assets at runtime.
  if [ -d /opt/kern-static ]; then
    log "INFO" "Found /opt/kern-static, copying to /app/static/kern"
    rm -rf /app/static/kern
    mkdir -p /app/static/kern
    cp -a /opt/kern-static/. /app/static/kern/
    log "INFO" "Copied kern static to /app/static/kern"
  else
    log "ERROR" "Required project assets directory /opt/kern-static was not found; cannot start xstandardanwendung. Ensure the Docker image includes or mounts /opt/kern-static before starting the container."
    exit 1
  fi

  # Keep /app paths owned by the app uid/gid.
  chown -R "${PUID}:${PGID}" /app || true
fi

# Wait for PostgreSQL and apply migrations before starting Django.
until run_as_app python manage.py migrate --noinput; do
  log "INFO" "waiting for db..."
  sleep 2
done

log "INFO" "Running collectstatic"
run_as_app python manage.py collectstatic --noinput
log "INFO" "collectstatic finished"

if [ "$#" -eq 0 ]; then
  set -- python manage.py runserver "${WEB_HOST}:${WEB_PORT}"
fi

if [ "$(id -u)" = "0" ]; then
  log "INFO" "Executing as ${PUID}:${PGID}: $*"
  exec gosu "${PUID}:${PGID}" "$@"
else
  log "INFO" "Executing: $*"
  exec "$@"
fi
