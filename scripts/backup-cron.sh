#!/bin/sh
set -eu

INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
DB_HOST="${DB_HOST:-mysql}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${MYSQL_DATABASE:-itam_system}"
DB_USER="${MYSQL_USER:-itam}"
DB_PASSWORD="${MYSQL_PASSWORD:-itam_pass}"

backup_once() {
  stamp="$(date +%Y%m%d-%H%M%S)"
  target="/backups/${stamp}"
  mkdir -p "$target"

  mysqldump \
    -h "$DB_HOST" \
    -P "$DB_PORT" \
    -u"$DB_USER" \
    -p"$DB_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    "$DB_NAME" | gzip > "$target/database.sql.gz"

  if [ -d /uploads ]; then
    tar -czf "$target/uploads.tar.gz" -C /uploads .
  fi

  cat > "$target/manifest.json" <<EOF
{"created_at":"$(date -Iseconds)","database":"database.sql.gz","uploads":"uploads.tar.gz","database_name":"$DB_NAME"}
EOF

  find /backups -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} +
  echo "Backup completed: $target"
}

while true; do
  backup_once
  sleep "$INTERVAL"
done
