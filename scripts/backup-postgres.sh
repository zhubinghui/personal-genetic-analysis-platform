#!/usr/bin/env bash
# =================================================================
# PostgreSQL 自动备份脚本
# 用法：./scripts/backup-postgres.sh
# 默认保留最近 30 天的备份
# =================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
RETENTION_DAYS=30

# 从 .env 读取数据库凭据（如果存在）
if [[ -f "${PROJECT_DIR}/.env" ]]; then
    export $(grep -E '^(POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD)=' "${PROJECT_DIR}/.env" | xargs)
fi

DB_NAME="${POSTGRES_DB:-genetic_platform}"
DB_USER="${POSTGRES_USER:-app_user}"
CONTAINER_NAME="$(cd "$PROJECT_DIR" && docker compose ps -q postgres 2>/dev/null || echo "")"

if [[ -z "$CONTAINER_NAME" ]]; then
    echo "[ERROR] PostgreSQL 容器未运行" >&2
    exit 1
fi

# 创建备份目录
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
DUMP_FILE="${BACKUP_DIR}/genetic_db_${TIMESTAMP}.dump"
COMPRESSED_FILE="${DUMP_FILE}.gz"

echo "[INFO] 开始备份 ${DB_NAME}..."
START_TIME=$(date +%s)

# 执行 pg_dump（自定义格式，支持并行恢复）
docker exec "$CONTAINER_NAME" pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -Fc \
    --no-owner \
    --no-privileges \
    | gzip > "$COMPRESSED_FILE"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
FILE_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)

echo "[INFO] 备份完成：${COMPRESSED_FILE}"
echo "[INFO] 文件大小：${FILE_SIZE}，耗时：${DURATION}s"

# 清理过期备份
DELETED=$(find "$BACKUP_DIR" -name "genetic_db_*.dump.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
if [[ "$DELETED" -gt 0 ]]; then
    echo "[INFO] 已清理 ${DELETED} 个超过 ${RETENTION_DAYS} 天的旧备份"
fi
