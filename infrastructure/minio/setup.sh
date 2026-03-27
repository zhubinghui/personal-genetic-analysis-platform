#!/bin/sh
set -e

echo "等待 MinIO 启动..."
sleep 3

# 配置 MinIO 客户端
mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

# 创建 bucket
mc mb --ignore-existing "local/$MINIO_BUCKET_IDAT"
mc mb --ignore-existing "local/$MINIO_BUCKET_REPORTS"

# 设置 bucket 策略为私有（默认已是私有，显式确认）
mc anonymous set none "local/$MINIO_BUCKET_IDAT"
mc anonymous set none "local/$MINIO_BUCKET_REPORTS"

# 设置生命周期：IDAT 原始文件 90 天后自动过期（用户可提前手动删除）
mc ilm add --expiry-days 90 "local/$MINIO_BUCKET_IDAT" || true

echo "MinIO bucket 初始化完成: $MINIO_BUCKET_IDAT, $MINIO_BUCKET_REPORTS"
