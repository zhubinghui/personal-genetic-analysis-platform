.PHONY: up down restart logs build migrate shell-db shell-back shell-worker test-back test-r test-analysis lint-back setup keys backup restore

# ── 基础操作 ─────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

build:
	docker compose build --no-cache

# ── 数据库 ───────────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

migrate-down:
	docker compose exec backend alembic downgrade -1

migrate-history:
	docker compose exec backend alembic history

shell-db:
	docker compose exec postgres psql -U $${POSTGRES_USER:-app_user} $${POSTGRES_DB:-genetic_platform}

# ── 进入容器 Shell ────────────────────────────────────────────
shell-back:
	docker compose exec backend bash

shell-worker:
	docker compose exec worker bash

# ── 测试 ─────────────────────────────────────────────────────
test-back:
	docker compose exec backend pytest tests/ -v

test-r:
	docker compose exec worker Rscript analysis/tests/run_tests.R

test-analysis:
	cd analysis && python -m pytest tests/ -v

# ── 代码质量 ─────────────────────────────────────────────────
lint-back:
	docker compose exec backend ruff check app/ && mypy app/

# ── 备份与恢复 ────────────────────────────────────────────────
backup:
	./scripts/backup-postgres.sh

restore:
	@test -n "$(DUMP)" || (echo "用法: make restore DUMP=backups/xxx.dump.gz" && exit 1)
	./scripts/restore-postgres.sh $(DUMP)

# ── 初始化 ───────────────────────────────────────────────────
setup: keys
	cp -n .env.example .env || true
	@echo "请编辑 .env 文件填写密钥后运行: make up && make migrate"

keys:
	@python3 -c "\
import secrets, base64; \
enc_key = base64.b64encode(secrets.token_bytes(32)).decode(); \
jwt_key = secrets.token_hex(32); \
print('FILE_ENCRYPTION_KEY=' + enc_key); \
print('JWT_SECRET_KEY=' + jwt_key)"
