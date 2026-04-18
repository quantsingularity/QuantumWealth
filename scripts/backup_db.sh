#!/usr/bin/env bash
# backup_db.sh -- Dump PostgreSQL database from running Docker container
set -euo pipefail

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
