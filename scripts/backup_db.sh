#!/usr/bin/env bash
# backup_db.sh -- Dump PostgreSQL database from running Docker container
set -euo pipefail

# FIX: `docker compose` only looks for docker-compose.yml in the current
# working directory, so this script previously failed with "no
# configuration file provided: not found" whenever it was run from
# anywhere other than the repo root (e.g. `cd scripts && ./backup_db.sh`).
# Always operate from the repo root, regardless of the caller's CWD.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# FIX: pick up the actually-configured DB_USER/DB_NAME from .env instead
# of silently falling back to the published defaults, which only work if
# the user never customized their database credentials.
if [ -f "code/backend/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "code/backend/.env"
  set +a
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${1:-./backups}"
BACKUP_FILE="$BACKUP_DIR/quantumwealth_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Backing up database to $BACKUP_FILE ..."
docker compose exec -T db pg_dump \
  -U "${DB_USER:-qwuser}" \
  "${DB_NAME:-quantumwealth}" \
  | gzip > "$BACKUP_FILE"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "Backup complete: $BACKUP_FILE ($SIZE)"
