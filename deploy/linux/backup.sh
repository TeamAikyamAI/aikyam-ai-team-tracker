#!/usr/bin/env bash
# Nightly backup: Postgres dump + uploaded BRDs, keep the last 14.
#   crontab: 30 2 * * * /opt/aikyam-tracker/deploy/linux/backup.sh
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/aikyam-tracker}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/aikyam-tracker}"
KEEP="${KEEP:-14}"
DB_NAME="${DB_NAME:-aikyam_ai_tracker}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"
pg_dump --format=custom --file="$BACKUP_DIR/db-$STAMP.dump" "$DB_NAME"
tar -czf "$BACKUP_DIR/uploads-$STAMP.tar.gz" -C "$APP_DIR/backend" uploads
ls -1t "$BACKUP_DIR"/db-*.dump | tail -n +$((KEEP + 1)) | xargs -r rm -f
ls -1t "$BACKUP_DIR"/uploads-*.tar.gz | tail -n +$((KEEP + 1)) | xargs -r rm -f
echo "backup ok: $BACKUP_DIR/db-$STAMP.dump"
# Restore:  pg_restore --clean --if-exists -d aikyam_ai_tracker db-<stamp>.dump
