# CLAUDE.md — 个人基因抗衰老分析平台

## 项目概述

基于 DNA 甲基化数据的个人衰老速率分析平台。用户上传 Illumina 甲基化芯片数据（IDAT 文件对或预处理 Beta CSV），平台异步运行 4 个经同行评审的表观遗传衰老时钟，生成含 9 大生理系统维度解读与循证干预建议的个性化报告。

---

## 项目架构

### 服务拓扑（Docker Compose，共 8 个服务）

```
用户浏览器
    │
    ▼
[Nginx :80]  ← 反向代理
    ├─ /api/  → [Backend FastAPI :8000]
    └─ /      → [Frontend Next.js :3000]
                      │
          [PostgreSQL :5432]  ← 用户/样本/任务/审计数据
          [Redis :6379]       ← Celery Broker + Result Backend
          [MinIO :9000]       ← 加密文件对象存储
          [Worker Celery]     ← R + Python 分析引擎
          [minio-init]        ← 初始化 Bucket（一次性）
```

### 目录结构

```
backend/
  app/
    api/v1/          # REST 路由：auth, samples, jobs, reports
    models/          # SQLAlchemy ORM：user, sample, analysis, audit
    services/        # 业务逻辑：storage_service, recommendation_engine, report_service, file_validator, consent_service
    utils/           # 工具函数：auth(JWT/bcrypt), encryption(AES-256-GCM), pseudonymization
    data/            # recommendations.json（310 条循证推荐数据库）
    config.py        # Pydantic Settings，从 .env 读取
    database.py      # SQLAlchemy async engine，pool_size=10
    main.py          # FastAPI 入口，含审计日志中间件
  alembic/           # 数据库迁移（当前：0001_initial_schema）

analysis/
  r_scripts/         # R 脚本：qc_normalize.R, horvath_clock.R, grimage.R, phenoage.R, dunedinpace.R
  pipeline/          # Python 编排层：orchestrator.py, r_bridge.py, result_parser.py, storage_adapter.py
  worker/            # Celery 任务定义：celery_app.py, tasks.py
  Dockerfile         # rocker/r-ver:4.4.0 + Python 3.10 + Bioconductor 包

frontend/
  src/
    app/             # Next.js 14 App Router 页面：login, register, consent, upload, dashboard, results/[jobId]
    components/      # 图表：AgeClockGauge, DunedinPaceRadar, AgingDimensionBars; 推荐：RecommendationCard
    lib/             # api.ts（HTTP 客户端）, hooks/useAnalysisJob.ts（任务轮询）
    types/           # index.ts，完整 TypeScript 类型定义

infrastructure/
  nginx/nginx.conf   # 反向代理，client_max_body_size 512MB
  postgres/init.sql  # pgcrypto + pg_trgm + updated_at 触发器
  minio/setup.sh     # 创建 idat-raw（90天过期）和 reports 两个 Bucket
```

### 核心数据流

```
上传 IDAT/Beta CSV
  → 文件验证（magic number / beta值范围）
  → AES-256-GCM 加密 → MinIO 存储
  → 创建 AnalysisJob（status=queued）
  → 推送 Celery 任务到 Redis 队列
  → Worker 拉取任务：
      1. 下载解密 → 临时目录
      2. qc_normalize.R（Noob + BMIQ）
      3. 并行 4 个时钟（ThreadPoolExecutor）
      4. 解析结果 → PostgreSQL
      5. 生成 JSON 报告 + ReportLab PDF
      6. 加密 PDF → MinIO
  → 前端 5 秒轮询 /jobs/{id}/status
  → 完成后渲染交互式报告
```

### API 路由（所有路由前缀 /api/v1）

| 路由 | 说明 |
|------|------|
| POST /auth/register | 注册 |
| POST /auth/login | 登录，返回 JWT |
| GET /auth/me | 当前用户信息 |
| POST /auth/consent | 记录知情同意 |
| POST /samples/upload/idat | 上传 IDAT 文件对 |
| POST /samples/upload/beta-csv | 上传 Beta CSV |
| GET /samples | 用户样本列表 |
| DELETE /samples/{id} | 软删除样本 |
| GET /jobs/{id}/status | 任务状态 |
| GET /jobs/{id}/result | 分析结果 |
| GET /reports/{id} | 完整报告 JSON |
| GET /reports/{id}/pdf | 流式下载加密 PDF |

---

## 开发规范和约定

### 隐私原则（强制）

- **所有分析数据必须使用 `pseudonym_id`，严禁使用 `user.id`**
- 通过 `app/utils/pseudonymization.py` 的 `get_pseudonym_id()` 统一访问
- Sample、AnalysisJob、AnalysisResult 的外键均指向 `pseudonym_id`，不关联 `user.id`
- MinIO 文件路径格式：`{pseudonym_id}/{sample_id}/{filename}.enc`

### 加密规范

- 所有上传文件必须经 `storage_service.upload_encrypted()` 存储，使用 AES-256-GCM
- 密钥来源：环境变量 `FILE_ENCRYPTION_KEY`（base64 编码 32 字节）
- GCM tag 必须验证，不得跳过 `InvalidTag` 异常
- 密码哈希使用 bcrypt cost=12，通过 `utils/auth.py` 的 `hash_password()` / `verify_password()`

### 数据库规范

- 使用 SQLAlchemy 异步 API（`AsyncSession`），通过 `get_db()` 依赖注入
- 新增数据库变更必须创建 Alembic 迁移文件，不得直接修改表结构
- 删除操作使用软删除（设置 `deleted_at` 时间戳），不得物理删除用户数据
- 查询时过滤 `deleted_at IS NULL`

### 后端代码规范

- Python 3.12，使用 `ruff` 做 lint，`mypy` 做类型检查
- FastAPI 路由函数使用 async/await
- 业务逻辑放在 `services/`，路由层只做参数校验和响应组装
- 使用 `structlog` 记录日志，包含结构化字段（job_id、sample_id 等）
- 审计日志由中间件自动记录，无需在路由中手动添加

### R 脚本规范

- 所有 R 脚本通过 `pipeline/r_bridge.py` 的 `run_r_script()` 调用
- R 脚本通过 stdin 接收 JSON 参数，通过 stdout 输出 JSON 结果
- 错误信息输出到 stderr，Python 侧抛出 `RScriptError`
- NaN/Inf 在 `result_parser.py` 的 `_to_float()` 中转换为 None

### 前端规范

- Next.js 14 App Router，TypeScript 严格模式
- API 调用统一通过 `src/lib/api.ts`，不得在组件中直接调用 fetch
- JWT token 存储于 localStorage，key 为 `access_token`
- 任务状态轮询使用 `hooks/useAnalysisJob.ts`，间隔 5 秒
- 类型定义统一在 `src/types/index.ts`

### 推荐引擎规范

- 推荐数据源为 `backend/app/data/recommendations.json`
- 每条推荐必须包含：`pmid`（PubMed ID）、`evidence_level`（GRADE A/B/C）、`category`（系统维度）
- 修改推荐数据需同步更新 `recommendation_engine.py` 的维度映射逻辑

---

## 常用命令

### 启动与停止

```bash
make up           # 启动所有服务（后台）
make down         # 停止所有服务
make restart      # 重启所有服务
make build        # 重新构建所有镜像（无缓存，首次约 30-60 分钟）
make logs         # 跟踪所有服务日志
```

### 数据库迁移

```bash
make migrate              # 运行所有未执行的迁移（alembic upgrade head）
make migrate-down         # 回滚一个版本
make migrate-history      # 查看迁移历史
make shell-db             # 进入 PostgreSQL 交互式 shell
```

### 调试

```bash
make shell-back           # 进入 backend 容器 bash
make shell-worker         # 进入 worker 容器 bash
docker compose logs -f backend    # 查看后端日志
docker compose logs -f worker     # 查看分析 Worker 日志
docker compose logs -f frontend   # 查看前端日志
```

### 测试

```bash
make test-back            # 运行 Python pytest（backend/tests/）
make test-r               # 运行 R 测试脚本（analysis/tests/run_tests.R）
make lint-back            # ruff check + mypy 类型检查
```

### 初始化

```bash
make setup                # 复制 .env.example → .env，提示填写密钥
make keys                 # 生成 FILE_ENCRYPTION_KEY 和 JWT_SECRET_KEY
```

### 健康检查

```bash
curl http://localhost:8000/health
# 返回：{"status":"ok","version":"0.1.0"}

docker compose ps         # 查看所有服务状态
```

### 开发模式说明

- 开发时使用 `docker-compose.override.yml` 自动激活，提供：
  - 后端热重载（volume mount）
  - API 文档：http://localhost:8000/api/docs
  - MinIO 控制台：http://localhost:9001
- 生产部署去除 override 文件，API 文档自动关闭

---

## Claude 需遵守的特殊规则

### 安全红线（不得违反）

1. **不得在代码中硬编码任何密钥、密码、token**。所有敏感值必须通过环境变量（`Settings` 类）注入。
2. **不得在日志中输出用户 PII 或原始遗传数据**。日志只能包含 UUID、状态码、指标数值等非敏感信息。
3. **不得绕过 AES-256-GCM 加密直接写入 MinIO**。所有文件必须经 `storage_service.upload_encrypted()` 处理。
4. **不得将 `user.id` 用于分析数据关联**。必须使用 `pseudonym_id`，违反此规则会破坏隐私隔离设计。
5. **不得物理删除用户遗传数据记录**。使用软删除模式，保留审计轨迹。

### 科学准确性

6. **GrimAge 当前使用 Hannum 算法作代理**（R 包限制）。任何涉及 GrimAge 的代码或说明必须标注此限制，不得作为完整 GrimAge 实现对外宣传。
7. **DunedinPACE 维度分数是相对衰老速率**（1.0 = 人群均值），不是年龄绝对值。推荐文案和图表标签必须体现此语义。

### 代码修改约束

8. **新增数据库字段必须创建 Alembic 迁移文件**，不得修改已有迁移文件中的历史内容。
9. **修改 R 脚本的 JSON 输入/输出格式时，必须同步更新 `r_bridge.py` 和 `result_parser.py`**，三者必须保持一致。
10. **推荐引擎的维度 key 名称（如 `cardiovascular_blood_pressure`）在 JSON 和 Python 代码中必须完全一致**，修改时需全局搜索确认。

### 架构约束

11. **Worker 分析任务必须是幂等的**。任务重试（最多 2 次）时不得产生重复的 AnalysisResult 记录。
12. **前端不得直接访问 MinIO 或 PostgreSQL**。所有数据交互必须通过 Backend API。
13. **R 脚本通过子进程调用，不得引入 Python-R 混合执行逻辑**。Python 侧只负责参数传递和结果解析。

### 合规意识

14. **任何新增的用户数据字段都需评估是否属于个人信息**，若是，需在 `audit.py` 模型中补充审计覆盖。
15. **医疗相关表述须保守措辞**：本平台结果仅供健康管理参考，不构成医疗诊断。代码注释、报告文案、API 响应中不得出现"诊断"、"治疗"等医疗声明。
