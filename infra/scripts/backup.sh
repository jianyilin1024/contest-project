#!/usr/bin/env bash
# 数据库每日备份，保留最近 14 天
# 建议加入 crontab：0 3 * * * bash /home/deploy/contest-project/infra/scripts/backup.sh
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
cd "$APP_DIR"

source .env.prod
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
  | gzip > "$BACKUP_DIR/db_$STAMP.sql.gz"

echo "备份完成：$BACKUP_DIR/db_$STAMP.sql.gz"
find "$BACKUP_DIR" -name 'db_*.sql.gz' -mtime +"$KEEP_DAYS" -delete
