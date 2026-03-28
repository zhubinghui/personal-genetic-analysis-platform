#!/usr/bin/env bash
# =================================================================
# 个人基因抗衰老分析平台 — 中国大陆服务器一键部署脚本
# 适用系统：Ubuntu 22.04 LTS
# 前置要求：已在阿里云 ACR 推送好三个镜像（由 GitHub Actions 完成）
#
# 使用方法：
#   1. 将此脚本上传到服务器
#   2. chmod +x deploy-china.sh
#   3. sudo ./deploy-china.sh
# =================================================================

set -euo pipefail

# ── 颜色输出 ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 必填配置（部署前修改这里）────────────────────────────────
REPO_URL="https://github.com/zhubinghui/personal-genetic-analysis-platform.git"
DEPLOY_DIR="/opt/genetic-platform"
DOMAIN=""                  # 填写你的域名，留空则跳过 HTTPS 配置
ACR_REGISTRY=""            # 例：registry.cn-hangzhou.aliyuncs.com
ACR_NAMESPACE=""           # 例：genetic-platform
ACR_USERNAME=""            # 阿里云账号用户名（邮箱）
ACR_PASSWORD=""            # ACR 登录密码

# ── 参数检查 ─────────────────────────────────────────────────
[[ -z "$ACR_REGISTRY" ]]   && error "请在脚本中填写 ACR_REGISTRY"
[[ -z "$ACR_NAMESPACE" ]]  && error "请在脚本中填写 ACR_NAMESPACE"
[[ -z "$ACR_USERNAME" ]]   && error "请在脚本中填写 ACR_USERNAME"
[[ -z "$ACR_PASSWORD" ]]   && error "请在脚本中填写 ACR_PASSWORD"
[[ $EUID -ne 0 ]]          && error "请使用 sudo 运行此脚本"

info "====== 开始部署（$(date '+%Y-%m-%d %H:%M:%S')）======"

# ═══════════════════════════════════════════════════════════════
# 步骤 1：安装 Docker + Docker Compose
# ═══════════════════════════════════════════════════════════════
install_docker() {
    if command -v docker &>/dev/null; then
        info "Docker 已安装：$(docker --version)"
        return
    fi
    info "安装 Docker（使用阿里云镜像）..."
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg lsb-release

    # 使用阿里云 Docker CE 源（国内稳定）
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://mirrors.aliyun.com/docker-ce/linux/ubuntu \
        $(lsb_release -cs) stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    info "Docker 安装完成：$(docker --version)"
}

# ═══════════════════════════════════════════════════════════════
# 步骤 2：配置 Docker 镜像加速（国内拉取 postgres/redis/minio 等官方镜像）
# ═══════════════════════════════════════════════════════════════
configure_docker_mirror() {
    info "配置 Docker 镜像加速..."
    mkdir -p /etc/docker
    # 同时配置多个加速源，任一可用即可
    cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://dockerhub.icu",
    "https://hub-mirror.c.163.com"
  ],
  "log-driver": "json-file",
  "log-opts": { "max-size": "100m", "max-file": "3" }
}
EOF
    systemctl daemon-reload
    systemctl restart docker
    info "Docker 镜像加速配置完成"
}

# ═══════════════════════════════════════════════════════════════
# 步骤 3：克隆或更新代码仓库
# ═══════════════════════════════════════════════════════════════
setup_repo() {
    if [[ -d "$DEPLOY_DIR/.git" ]]; then
        info "更新代码仓库..."
        git -C "$DEPLOY_DIR" pull origin master
    else
        info "克隆代码仓库到 $DEPLOY_DIR ..."
        git clone "$REPO_URL" "$DEPLOY_DIR"
    fi
}

# ═══════════════════════════════════════════════════════════════
# 步骤 4：生成 .env 配置文件
# ═══════════════════════════════════════════════════════════════
setup_env() {
    ENV_FILE="$DEPLOY_DIR/.env"

    if [[ -f "$ENV_FILE" ]]; then
        warn ".env 文件已存在，跳过生成（如需重新生成请手动删除）"
        return
    fi

    info "生成 .env 配置文件..."

    # 生成随机密钥
    ENC_KEY=$(openssl rand -base64 32)
    JWT_KEY=$(openssl rand -hex 32)
    PG_PASS=$(openssl rand -hex 16)
    MINIO_PASS=$(openssl rand -hex 16)

    cat > "$ENV_FILE" <<EOF
# ============================
# 自动生成 — $(date '+%Y-%m-%d %H:%M:%S')
# ============================

# ---- PostgreSQL ----
POSTGRES_DB=genetic_platform
POSTGRES_USER=app_user
POSTGRES_PASSWORD=${PG_PASS}
DATABASE_URL=postgresql+asyncpg://app_user:${PG_PASS}@postgres:5432/genetic_platform
DATABASE_URL_SYNC=postgresql://app_user:${PG_PASS}@postgres:5432/genetic_platform

# ---- Redis ----
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# ---- MinIO（自建，国内服务器本地存储）----
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=${MINIO_PASS}
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET_IDAT=idat-raw
MINIO_BUCKET_REPORTS=reports
MINIO_BUCKET_KNOWLEDGE=knowledge-docs
MINIO_USE_SSL=false

# ---- 文件加密 ----
FILE_ENCRYPTION_KEY=${ENC_KEY}

# ---- JWT ----
JWT_SECRET_KEY=${JWT_KEY}
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=60
JWT_REFRESH_EXPIRE_DAYS=30

# ---- 应用 ----
ENVIRONMENT=production
LOG_LEVEL=INFO
API_BASE_URL=https://${DOMAIN:-localhost}
FRONTEND_URL=https://${DOMAIN:-localhost}
ALLOWED_ORIGINS=https://${DOMAIN:-localhost}
CONSENT_VERSION=1.0

# ---- 前端 ----
NEXT_PUBLIC_API_URL=
NEXT_INTERNAL_API_URL=http://backend:8000

# ---- ACR 镜像配置 ----
ACR_REGISTRY=${ACR_REGISTRY}
ACR_NAMESPACE=${ACR_NAMESPACE}

# ---- HuggingFace 国内镜像（fastembed 模型下载）----
HF_ENDPOINT=https://hf-mirror.com

# ---- LLM（选填，按需配置国内 API）----
# OPENAI_API_KEY=sk-xxx
# OPENAI_BASE_URL=https://api.deepseek.com/v1    # DeepSeek 兼容 OpenAI 格式
# DASHSCOPE_API_KEY=sk-xxx                        # 阿里云百炼 / 通义千问
EOF

    chmod 600 "$ENV_FILE"
    info ".env 文件已生成，密钥已随机化"
    warn "请检查并按需填写 LLM API 密钥等可选配置：$ENV_FILE"
}

# ═══════════════════════════════════════════════════════════════
# 步骤 5：登录 ACR 并拉取镜像
# ═══════════════════════════════════════════════════════════════
pull_images() {
    info "登录阿里云 ACR..."
    echo "$ACR_PASSWORD" | docker login "$ACR_REGISTRY" \
        --username "$ACR_USERNAME" --password-stdin

    info "拉取应用镜像（backend / frontend / worker）..."
    docker pull "${ACR_REGISTRY}/${ACR_NAMESPACE}/genetic-platform-backend:latest"
    docker pull "${ACR_REGISTRY}/${ACR_NAMESPACE}/genetic-platform-frontend:latest"
    docker pull "${ACR_REGISTRY}/${ACR_NAMESPACE}/genetic-platform-worker:latest"

    info "拉取基础服务镜像（postgres / redis / minio）..."
    # 这些镜像来自 Docker Hub，走上面配置的国内加速镜像
    docker pull pgvector/pgvector:pg16 || warn "pgvector 拉取失败，请检查 Docker 镜像加速配置"
    docker pull redis:7-alpine
    docker pull minio/minio:latest
    docker pull minio/mc:latest
    docker pull nginx:1.25-alpine
}

# ═══════════════════════════════════════════════════════════════
# 步骤 6：启动服务
# ═══════════════════════════════════════════════════════════════
start_services() {
    info "启动所有服务..."
    cd "$DEPLOY_DIR"
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    info "等待 PostgreSQL 就绪（最多 60 秒）..."
    for i in $(seq 1 12); do
        if docker compose exec -T postgres pg_isready -U app_user -d genetic_platform &>/dev/null; then
            info "PostgreSQL 已就绪"
            break
        fi
        [[ $i -eq 12 ]] && error "PostgreSQL 启动超时，请检查日志：docker compose logs postgres"
        sleep 5
    done
}

# ═══════════════════════════════════════════════════════════════
# 步骤 7：运行数据库迁移
# ═══════════════════════════════════════════════════════════════
run_migrations() {
    info "运行 Alembic 数据库迁移..."
    cd "$DEPLOY_DIR"
    docker compose exec -T backend alembic upgrade head
    info "数据库迁移完成"
}

# ═══════════════════════════════════════════════════════════════
# 步骤 8：配置宿主机 Nginx + HTTPS（可选，仅在填写 DOMAIN 时执行）
# ═══════════════════════════════════════════════════════════════
setup_nginx_https() {
    [[ -z "$DOMAIN" ]] && { warn "未填写 DOMAIN，跳过 Nginx/HTTPS 配置"; return; }

    info "安装 Nginx + Certbot..."
    apt-get install -y -qq nginx certbot python3-certbot-nginx

    info "生成 Nginx 配置..."
    cat > /etc/nginx/sites-available/genetic-platform <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    # Let's Encrypt 验证
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://\$host\$request_uri; }
}

server {
    listen 443 ssl;
    server_name ${DOMAIN};

    # SSL 证书（由 Certbot 填充）
    ssl_certificate     /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # 上传大文件限制（IDAT 文件约 4-8 MB，PDF 可更大）
    client_max_body_size 512M;

    # 代理到 Docker Nginx 容器
    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_read_timeout 300s;
    }
}
EOF

    ln -sf /etc/nginx/sites-available/genetic-platform /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx

    info "申请 Let's Encrypt SSL 证书..."
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
        --email "admin@${DOMAIN}" --redirect || \
        warn "SSL 证书申请失败，请手动运行：certbot --nginx -d ${DOMAIN}"

    # 自动续期
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && systemctl reload nginx") | crontab -
    info "SSL 证书自动续期已配置"
}

# ═══════════════════════════════════════════════════════════════
# 步骤 9：配置 systemd 开机自启
# ═══════════════════════════════════════════════════════════════
setup_autostart() {
    info "配置开机自启..."
    cat > /etc/systemd/system/genetic-platform.service <<EOF
[Unit]
Description=Genetic Analysis Platform
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${DEPLOY_DIR}
ExecStart=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable genetic-platform
    info "开机自启已配置"
}

# ═══════════════════════════════════════════════════════════════
# 步骤 10：健康检查
# ═══════════════════════════════════════════════════════════════
health_check() {
    info "执行健康检查..."
    sleep 5

    BASE_URL="http://127.0.0.1:8080"
    HEALTH=$(curl -sf "${BASE_URL}/api/health" 2>/dev/null || echo "FAIL")

    if echo "$HEALTH" | grep -q '"status"'; then
        info "健康检查通过：$HEALTH"
    else
        warn "健康检查未通过，服务可能仍在启动中"
        warn "请稍后手动检查：curl http://127.0.0.1:8080/api/health"
    fi
}

# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════
main() {
    install_docker
    configure_docker_mirror
    setup_repo
    setup_env
    pull_images
    start_services
    run_migrations
    setup_nginx_https
    setup_autostart
    health_check

    echo ""
    info "====== 部署完成 ======"
    info "服务地址："
    [[ -n "$DOMAIN" ]] && info "  HTTPS: https://${DOMAIN}" || info "  HTTP:  http://<服务器IP>"
    info "管理后台：/admin/knowledge（需管理员账号）"
    info "API 文档：仅开发环境可见（生产环境已关闭）"
    info ""
    info "常用运维命令："
    info "  查看日志：docker compose logs -f backend"
    info "  重启服务：docker compose -f docker-compose.yml -f docker-compose.prod.yml restart"
    info "  更新镜像：docker compose pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
}

main "$@"
