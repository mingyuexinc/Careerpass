#!/usr/bin/env sh
set -eu

umask 077

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BACKEND_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
COMPOSE_FILE=${COMPOSE_FILE:-"$BACKEND_DIR/../docker-compose.production.yml"}
ENV_FILE=${ENV_FILE:-"$BACKEND_DIR/.env.production"}
BACKUP_DIR=${BACKUP_DIR:-"$BACKEND_DIR/backups"}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

if [ ! -f "$ENV_FILE" ]; then
  echo "production env file not found" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

compose ps postgres backend >/dev/null

compose exec -T postgres sh -c \
  'pg_dump --format=custom --no-owner --no-acl -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  > "$BACKUP_DIR/postgres-$STAMP.dump"

compose exec -T backend tar -czf - -C /var/lib/careerpass/objects . \
  > "$BACKUP_DIR/objects-$STAMP.tar.gz"

sha256sum "$BACKUP_DIR/postgres-$STAMP.dump" "$BACKUP_DIR/objects-$STAMP.tar.gz" \
  > "$BACKUP_DIR/manifest-$STAMP.sha256"

# Keep a bounded local staging history. Copy selected backups outside the server separately.
find "$BACKUP_DIR" -maxdepth 1 -type f -mtime +14 -delete

echo "created backup set: $STAMP"
