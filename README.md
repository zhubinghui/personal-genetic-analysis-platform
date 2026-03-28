# 个人基因抗衰老分析平台

基于 DNA 甲基化数据的个人衰老速率分析平台。用户上传血液甲基化芯片数据（IDAT 文件），平台自动运行四个经过同行评审的衰老时钟算法，生成含 9 大生理系统维度解读与循证干预建议的个性化报告。

## 功能概览

### 核心分析

- **四大衰老时钟**：Horvath Clock、GrimAge（Hannum 代理）、PhenoAge、DunedinPACE
- **9 系统维度分析**：基于 DunedinPACE 173 个模型探针，按心血管、代谢、肾脏、肝脏、肺功能、免疫、牙周、认知、身体功能分组计算相对衰老速率
- **循证推荐引擎**：根据维度评分匹配个性化干预建议，每条建议含 PubMed 文献引用与证据等级（GRADE 标准）
- **交互式报告**：雷达图、条形图、时钟对比可视化，支持 PDF 导出

### 知识库 & RAG（v0.2 新增）

- **本地向量知识库**：管理员上传学术文献（PDF/DOCX/TXT），自动解析、分块、生成本地嵌入向量（fastembed ONNX，无需外部 API）
- **pgvector 向量搜索**：基于 PostgreSQL pgvector 扩展的 HNSW 余弦相似度索引，毫秒级语义检索
- **RAG 整合报告**：每条抗衰老建议自动检索知识库相关文献，附加"知识库文献支撑"折叠面板，提供可展开的原文片段与相关度评分

### 纵向对比 & 同龄对标（v0.2 新增）

- **历史趋势分析**：多次采样的衰老时钟折线图、DunedinPACE 速率趋势、9 大系统维度雷达叠加对比、历史数据明细表
- **同龄人群对标**：实时计算用户在 5 年年龄组中的百分位排名，4 项核心指标各一个百分位进度条，显示同龄均值 ± 标准差

### 用户体验（v0.2 新增）

- **品牌登录页**：分屏布局（左侧产品介绍 + 右侧表单）、密码强度指示条、邮箱实时校验
- **全局导航栏**：统一顶部导航（控制台 / 历史对比 / 上传 / 知识库 / 用户管理），管理员菜单自动显示
- **术语提示系统**：40+ 专业名词词典，悬停 `?` 图标显示详细解释（衰老时钟、维度、生物标志物、证据等级）
- **深色模式**：Tailwind dark mode + 本地持久化主题偏好
- **数据自管理**：用户可删除自己的采样数据（GDPR 软删除）
- **JWT 自动续签**：到期前 5 分钟自动刷新 Token，避免操作中断
- **404 错误页**：品牌风格友好错误页面

### 管理员功能（v0.2 新增）

- **知识库管理**：文献上传 / 列表 / 删除 / 重新向量化 / 语义搜索测试
- **文献去重**：上传时自动计算 SHA-256，同一文件内容只允许上传一次，返回已存在文献的标题与日期
- **用户管理**：用户列表 / 设置管理员角色 / 启用或禁用账号
- **管理员入口**：导航栏为 `is_admin` 用户自动显示管理菜单

### 质量保障（v0.2 新增）

- **自动化测试**：58 个 pytest 测试用例覆盖加密、文件校验、推荐引擎、伪名化、Auth API、知识库 API、RAG 服务
- **CI/CD 流水线**：GitHub Actions — lint（ruff + mypy）→ test（pgvector + Redis）→ frontend check → Docker build 验证

### 隐私与安全

- 用户数据与分析数据通过 `pseudonym_id` 隔离，不直接关联
- 所有上传文件使用 AES-256-GCM 加密存储于 MinIO
- 用户密码使用 bcrypt 哈希存储
- 所有 POST/PUT/DELETE 操作记录审计日志
- 上传前强制完成知情同意流程

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 + TypeScript + Tailwind CSS + Recharts |
| 后端 | Python FastAPI + SQLAlchemy 2.0 + Alembic |
| 分析引擎 | R 4.4 + methylclock + DunedinPACE + Bioconductor |
| 向量数据库 | PostgreSQL 16 + pgvector（HNSW 索引） |
| 嵌入模型 | fastembed + BAAI/bge-small-en-v1.5（384 维，ONNX 本地运行） |
| 任务队列 | Celery + Redis |
| 存储 | PostgreSQL 16 + MinIO（对象存储） |
| 测试 | pytest + pytest-asyncio + GitHub Actions CI |
| 部署 | Docker Compose |

## 快速开始

### 环境要求

- Docker 24+
- Docker Compose v2+
- 8GB+ 内存（R 包加载需要）
- 50GB+ 磁盘（R/Bioconductor 包约 10GB，数据存储另计）

### 部署步骤

```bash
# 1. 克隆仓库
git clone https://github.com/zhubinghui/personal-genetic-analysis-platform.git
cd personal-genetic-analysis-platform

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，修改以下关键配置：
# - POSTGRES_PASSWORD
# - JWT_SECRET_KEY（建议用 openssl rand -hex 32 生成）
# - FILE_ENCRYPTION_KEY（建议用 python3 -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())" 生成）
# - MINIO_ROOT_PASSWORD
# - RESEND_API_KEY（邮箱验证，见下方「邮件 & 短信配置」）

# 3. 构建镜像（首次约 30-60 分钟，主要是 R 包编译）
docker compose build

# 4. 启动服务
docker compose up -d

# 5. 初始化数据库
docker compose exec backend alembic upgrade head

# 6. 设置管理员账号
docker compose exec postgres psql -U app_user -d genetic_platform \
  -c "UPDATE users SET is_admin=true WHERE email='your-admin@example.com';"

# 7. 访问平台
# 前端：http://localhost:3000
# 后端 API：http://localhost:8000/api/docs
```

### 验证部署

```bash
# 检查所有服务状态
docker compose ps

# 后端健康检查
curl http://localhost:8000/health
# 返回：{"status":"ok","version":"0.1.0"}

# 运行测试
docker compose exec backend pytest tests/ -v
```

## 分析流程

```
用户上传 IDAT 文件（Red + Green 双通道）
        |
    QC 归一化（Noob + BMIQ）
        |
   +----------------------------+
   |  并行运行四个衰老时钟       |
   |  Horvath / GrimAge /       |
   |  PhenoAge / DunedinPACE    |
   +----------------------------+
        |
  DunedinPACE 系统维度计算
  （探针加权贡献 -> 9 大系统）
        |
   推荐引擎匹配循证建议
   + RAG 知识库文献检索
        |
   生成 JSON 报告 + PDF
```

典型分析耗时：5-15 分钟（取决于服务器配置）

## 项目结构

```
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/         # REST API 路由
│   │   │   └── admin/      # 管理员 API（知识库 + 用户管理）
│   │   ├── models/         # 数据库模型（含 knowledge.py 向量模型）
│   │   ├── services/       # 业务逻辑
│   │   │   ├── recommendation_engine.py  # 循证推荐引擎
│   │   │   ├── report_service.py         # 报告生成 + 同龄对标
│   │   │   ├── rag_service.py            # RAG 知识库检索
│   │   │   ├── embedding_service.py      # 本地嵌入模型
│   │   │   ├── knowledge_service.py      # 知识库 CRUD + 语义搜索
│   │   │   ├── trend_service.py          # 纵向对比
│   │   │   └── benchmark_service.py      # 同龄百分位对标
│   │   ├── utils/          # 加密、认证、伪名化
│   │   └── data/           # 推荐数据库（recommendations.json）
│   ├── alembic/            # 数据库迁移
│   └── tests/              # pytest 测试套件（58 个用例）
├── analysis/               # Celery Worker + R 分析引擎
│   ├── r_scripts/          # R 脚本（5 个时钟 + QC）
│   ├── pipeline/           # Python 编排层
│   └── worker/             # Celery 任务定义
├── frontend/               # Next.js 14 前端
│   └── src/
│       ├── app/            # 页面（登录/注册/控制台/报告/趋势/管理）
│       ├── components/
│       │   ├── charts/     # 时钟仪表盘、雷达图、维度条形图
│       │   ├── report/     # 推荐卡片、同龄对标组件
│       │   ├── layout/     # 全局导航栏
│       │   └── ui/         # 术语提示组件（InfoTip）
│       └── lib/            # API 客户端、术语词典、Token 续签
├── infrastructure/
│   ├── nginx/              # 反向代理配置
│   ├── postgres/           # 数据库初始化（含 pgvector 扩展）
│   └── minio/              # 对象存储初始化（含知识库 bucket）
├── .github/workflows/      # CI/CD 流水线
├── docker-compose.yml      # 生产编排
├── docker-compose.override.yml  # 开发模式覆盖
└── .env.example            # 环境变量模板
```

## 数据格式支持

| 格式 | 说明 |
|------|------|
| IDAT（双文件） | Illumina EPIC 850K / 450K 芯片原始数据 |
| Beta CSV | 预处理后的甲基化 beta 值矩阵（探针 x 样本） |

## 衰老时钟说明

| 时钟 | 参考文献 | 特点 |
|------|---------|------|
| Horvath Clock | Horvath, 2013, Genome Biology | 多组织泛组织时钟 |
| GrimAge | Lu et al., 2019, Aging | 死亡率预测，使用 Hannum 作代理（当前 R 包限制） |
| PhenoAge | Levine et al., 2018, Aging | 整合临床表型的生物学年龄 |
| DunedinPACE | Belsky et al., 2022, eLife | 衰老速率（非绝对年龄），1.0 = 人群均值 |

## 开发模式

```bash
# 启动开发模式（热重载）
docker compose up -d

# 查看后端日志
docker compose logs -f backend

# 查看分析 Worker 日志
docker compose logs -f worker

# 运行数据库迁移
docker compose exec backend alembic upgrade head

# 运行后端测试
docker compose exec backend pytest tests/ -v

# 运行 lint 检查
docker compose exec backend ruff check app/ && mypy app/
```

## 邮件 & 短信验证配置

平台支持**邮箱验证码**和**短信验证码**双通道，用户注册后需验证邮箱方可登录。至少需要配置一个通道。

### 邮箱通道：Resend API（推荐）

[Resend](https://resend.com) 是现代邮件 API 服务，免费额度 3000 封/月，仅需一个 API Key，无需配置 SMTP 服务器。

```bash
# 1. 注册 https://resend.com（支持 GitHub 登录）
# 2. 在 Dashboard → API Keys 创建 Key
# 3. 添加到 .env：

RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
EMAIL_FROM_ADDRESS=onboarding@resend.dev   # 免费版可用 resend.dev 域名发信
EMAIL_FROM_NAME=基因抗衰老分析平台

# 如需自定义发信域名（如 noreply@yourdomain.com），在 Resend 控制台添加域名并配置 DNS
```

### 短信通道：阿里云短信（可选）

[阿里云短信服务](https://dysms.console.aliyun.com) 支持国内手机号，约 0.04 元/条。

```bash
# 1. 登录阿里云控制台 → 短信服务
# 2. 创建 RAM 子用户（仅授予 AliyunDysmsFullAccess 权限），获取 AccessKey
# 3. 添加短信签名（如「基因分析平台」），等待审核通过
# 4. 添加短信模板，内容如：「您的验证码为${code}，10分钟内有效。」，等待审核通过
# 5. 添加到 .env：

ALIYUN_ACCESS_KEY_ID=LTAI5txxxxxxxxxxxxxxxxxx
ALIYUN_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALIYUN_SMS_SIGN_NAME=基因分析平台
ALIYUN_SMS_TEMPLATE_CODE=SMS_27xxxxx

# 验证码有效期（两个通道共用）
VERIFY_CODE_EXPIRE_MINUTES=10
```

### 验证流程说明

| 场景 | 流程 |
|---|---|
| **注册** | 填写邮箱 + 密码 + 可选手机号 → 自动发验证码到邮箱 → 输入 6 位验证码 → 账号激活 |
| **登录** | 未验证用户返回 403，提示验证邮箱，可一键重发验证码 |
| **忘记密码** | 选择邮箱或短信通道 → 收到重置验证码 → 输入验证码 + 新密码 → 重置成功 |

> **注意**：未配置 Resend API Key 时，验证码发送会被静默跳过，新注册用户将无法完成验证。建议部署前务必配置至少一个通道。

## 第三方登录配置

支持 GitHub / Google / 微信三种 OAuth2 登录，按需配置。未配置的平台按钮不会显示。

### GitHub

```bash
# 1. GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
# 2. Homepage URL: http://localhost:3000
# 3. Callback URL: http://localhost:8000/api/v1/auth/oauth/github/callback
# 4. 添加到 .env：

GITHUB_CLIENT_ID=Ov23lixxxxxxxxxx
GITHUB_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Google

```bash
# 1. Google Cloud Console → APIs & Services → Credentials → Create OAuth 2.0 Client
# 2. Authorized redirect URI: http://localhost:8000/api/v1/auth/oauth/google/callback
# 3. 添加到 .env：

GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxx
```

### 微信（需企业认证）

```bash
# 1. 注册微信开放平台: https://open.weixin.qq.com
# 2. 完成企业认证（300 元/年）
# 3. 创建网站应用，获取 AppID
# 4. 添加到 .env：

WECHAT_APP_ID=wxxxxxxxxxxx
WECHAT_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

```bash
# 通用设置
OAUTH_REDIRECT_BASE=http://localhost:8000   # 生产环境改为实际域名
```

## 更新日志

---

### v0.3.0 — 2026.03.28

---

#### 知识库强化
- 批量上传：多文件 + ZIP 压缩包（自动解压提取 PDF/DOCX/TXT）
- PDF 元数据自动提取：PyMuPDF 提取标题/作者/关键词，无需手动填写
- PDF 在线预览：流式传输，浏览器内直接查看文献

#### 多 LLM 大模型支持
- 可插拔 Provider 架构：Claude / ChatGPT / DeepSeek / Kimi
- DeepSeek/Kimi 复用 OpenAI SDK（自定义 base_url）
- 管理员设置页：选择 Provider、填写 API Key、模型名、Temperature
- 一键测试连接功能
- SystemSettings 数据库表存储动态配置

#### AI Chatbot 对话
- 报告页悬浮 💬 按钮，可展开对话面板
- 基于知识库文献 + 用户分析结果的 RAG 问答
- 引用来源显示（文献标题 + 页码 + 相关度）
- 预设推荐问题

#### AI 报告深度解读
- LLM 生成个性化衰老状态解读（200-300 字）
- 结合用户时钟评分 + 知识库文献上下文
- 包含整体评价、优势、关注点、可执行建议
- LLM 未配置时静默跳过（不影响现有功能）

---

### v0.2.2 — 2026.03.28

---

#### OAuth2 第三方登录
- 可插拔 Provider 架构：新增平台只需实现一个类 + 注册到字典
- GitHub 登录：即时可用，Settings → Developer settings → OAuth Apps
- Google 登录：即时可用，Google Cloud Console → OAuth 2.0
- 微信登录：代码已就绪，需企业认证通过后启用
- 自动账号关联：同一邮箱的三方账号与本地账号自动绑定
- OAuth 用户免邮箱验证（信任第三方平台）
- 登录/注册页自动检测已配置的 Provider 并显示按钮

---

### v0.2.1 — 2026.03.28

---

#### 双通道身份验证
- 邮箱验证：SMTP 替换为 Resend API（一个 API Key 即可，免费 3000 封/月）
- 短信验证：集成阿里云短信 API（国内号码全覆盖，约 0.04 元/条）
- 6 位数字验证码 + Redis 存储 + TTL 自动过期（替代原 JWT 链接方案）
- 注册时自动发送验证码，未验证用户登录返回 403
- 忘记密码：邮箱/短信双通道切换，验证码重置密码
- 用户模型新增 phone 字段（可选），注册时可同时绑定手机号

---

### v0.2.0 — 2026.03.28

---

#### 知识库 & RAG
- 本地向量知识库：pgvector + fastembed (BAAI/bge-small-en-v1.5, 384 维)
- 管理员文献上传界面（PDF/DOCX/TXT），自动解析分块与向量化
- RAG 整合报告：每条推荐自动附加知识库文献支撑

#### 纵向对比 & 同龄对标
- 历史趋势页面：4 时钟折线图 + DunedinPACE 速率趋势 + 维度雷达叠加
- 同龄人群百分位对标（5 年年龄组，4 项核心指标）

#### 测试 & CI/CD
- 58 个 pytest 测试用例（单元 + 集成）
- GitHub Actions CI 流水线（lint → test → frontend check → Docker build）

#### UI 大改版
- 分屏登录页 + 密码强度指示器 + 邮箱实时校验
- 全局导航栏 + 深色模式 + 术语提示系统（40+ 词条）
- Dashboard 数据概览卡片 + 采样删除功能
- 管理员用户管理（列表 / 角色 / 启禁用）
- JWT 自动续签 + 404 页面

#### Bug 修复
- 修复知识库列表页 401 轮询刷屏问题
- 修复趋势页同一样本多次分析导致数据重复（每样本仅取最新分析）

---

### v0.1.0 — 2026.03.27

---

- 初始版本：四大衰老时钟分析 + 循证推荐引擎 + 隐私加密架构
- 核心功能：IDAT/Beta CSV 上传 → QC 归一化 → 时钟计算 → 报告生成
- 基础设施：Docker Compose 全栈部署、MinIO 加密存储、审计日志

## 许可证

MIT License

## 免责声明

本平台基于 DNA 甲基化数据的计算分析，仅供健康管理参考，不构成医疗诊断、治疗建议或处方。如有健康问题请咨询专业医生。
