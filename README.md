# 个人基因抗衰老分析平台

基于 DNA 甲基化数据的个人衰老速率分析平台。用户上传血液甲基化芯片数据（IDAT 文件），平台自动运行四个经过同行评审的衰老时钟算法，生成含 9 大生理系统维度解读与循证干预建议的个性化报告。

## 功能概览

- **四大衰老时钟**：Horvath Clock、GrimAge（Hannum 代理）、PhenoAge、DunedinPACE
- **9 系统维度分析**：基于 DunedinPACE 173 个模型探针，按心血管、代谢、肾脏、肝脏、肺功能、免疫、牙周、认知、身体功能分组计算相对衰老速率
- **循证推荐引擎**：根据维度评分匹配个性化干预建议，每条建议含 PubMed 文献引用与证据等级（GRADE 标准）
- **交互式报告**：雷达图、条形图、时钟对比可视化，支持 PDF 导出
- **隐私保护**：伪名化存储、AES-256-GCM 文件加密、知情同意流程

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 + TypeScript + Tailwind CSS + Recharts |
| 后端 | Python FastAPI + SQLAlchemy + Alembic |
| 分析引擎 | R 4.4 + methylclock + DunedinPACE + Bioconductor |
| 任务队列 | Celery + Redis |
| 存储 | PostgreSQL 16 + MinIO（对象存储） |
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
# - FILE_ENCRYPTION_KEY（建议用 python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 生成）
# - MINIO_ROOT_PASSWORD

# 3. 构建镜像（首次约 30-60 分钟，主要是 R 包编译）
docker compose build

# 4. 启动服务
docker compose up -d

# 5. 初始化数据库
docker compose exec backend alembic upgrade head

# 6. 访问平台
# 前端：http://localhost:3000
# 后端 API：http://localhost:8000/docs
```

### 验证部署

```bash
# 检查所有服务状态
docker compose ps

# 后端健康检查
curl http://localhost:8000/health
# 返回：{"status":"ok","version":"0.1.0"}
```

## 分析流程

```
用户上传 IDAT 文件（Red + Green 双通道）
        ↓
    QC 归一化（Noob + BMIQ）
        ↓
   ┌────────────────────────────┐
   │  并行运行四个衰老时钟       │
   │  Horvath / GrimAge /       │
   │  PhenoAge / DunedinPACE   │
   └────────────────────────────┘
        ↓
  DunedinPACE 系统维度计算
  （探针加权贡献 → 9 大系统）
        ↓
   推荐引擎匹配循证建议
        ↓
   生成 JSON 报告 + PDF
```

典型分析耗时：5-15 分钟（取决于服务器配置）

## 项目结构

```
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/         # REST API 路由
│   │   ├── models/         # 数据库模型
│   │   ├── services/       # 业务逻辑（推荐引擎、报告生成）
│   │   ├── utils/          # 加密、认证、伪名化
│   │   └── data/           # 推荐数据库（recommendations.json）
│   └── alembic/            # 数据库迁移
├── analysis/               # Celery Worker + R 分析引擎
│   ├── r_scripts/          # R 脚本（5 个时钟 + QC）
│   ├── pipeline/           # Python 编排层
│   └── worker/             # Celery 任务定义
├── frontend/               # Next.js 14 前端
│   └── src/
│       ├── app/            # 页面（登录/上传/控制台/报告）
│       ├── components/     # 图表、推荐卡片等组件
│       └── lib/            # API 客户端、Hooks
├── infrastructure/
│   ├── nginx/              # 反向代理配置
│   ├── postgres/           # 数据库初始化
│   └── minio/              # 对象存储初始化
├── docker-compose.yml      # 生产编排
├── docker-compose.override.yml  # 开发模式覆盖
└── .env.example            # 环境变量模板
```

## 数据格式支持

| 格式 | 说明 |
|------|------|
| IDAT（双文件） | Illumina EPIC 850K / 450K 芯片原始数据 |
| Beta CSV | 预处理后的甲基化 beta 值矩阵（探针×样本） |

## 衰老时钟说明

| 时钟 | 参考文献 | 特点 |
|------|---------|------|
| Horvath Clock | Horvath, 2013, Genome Biology | 多组织泛组织时钟 |
| GrimAge | Lu et al., 2019, Aging | 死亡率预测，使用 Hannum 作代理（当前 R 包限制） |
| PhenoAge | Levine et al., 2018, Aging | 整合临床表型的生物学年龄 |
| DunedinPACE | Belsky et al., 2022, eLife | 衰老速率（非绝对年龄），1.0 = 人群均值 |

## 隐私与安全

- 用户数据与分析数据通过 `pseudonym_id` 隔离，不直接关联
- 所有上传文件使用 AES-256-GCM 加密存储于 MinIO
- 用户密码使用 bcrypt 哈希存储
- 所有 POST/PUT/DELETE 操作记录审计日志
- 上传前强制完成知情同意流程

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
```

## 许可证

MIT License

## 免责声明

本平台基于 DNA 甲基化数据的计算分析，仅供健康管理参考，不构成医疗诊断、治疗建议或处方。如有健康问题请咨询专业医生。
