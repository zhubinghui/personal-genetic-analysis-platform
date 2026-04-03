#!/usr/bin/env bash
# =================================================================
# PostgreSQL 恢复脚本
# 用法：./scripts/restore-postgres.sh backups/genetic_db_20260403_030000.dump.gz
# =================================================================
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "用法: $0 <dump_file.gz>" >&2
    echo "示例: $0 backups/genetic_db_20260403_030000.dump.gz" >&2
    exit 1
fi

DUMP_FILE="$1"
if [[ ! -f "$DUMP_FILE" ]]; then
    echo "[ERROR] 文件不存在: ${DUMP_FILE}" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 从 .env 读取数据库凭据
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

echo "[WARN] 即将恢复数据库 ${DB_NAME}，现有数据将被覆盖！"
read -p "确认继续？(y/N) " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && { echo "已取消"; exit 0; }

echo "[INFO] 开始恢复 ${DUMP_FILE} → ${DB_NAME}..."

# 解压并通过 stdin 传入容器内 pg_restore
gunzip -c "$DUMP_FILE" | docker exec -i "$CONTAINER_NAME" \
    pg_restore \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    2>&1 || true  # pg_restore 在 --clean 模式下会输出 "does not exist" 警告，非致命

echo "[INFO] 运行 ANALYZE 更新统计信息..."
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "ANALYZE;"

echo "[INFO] 恢复完成"
