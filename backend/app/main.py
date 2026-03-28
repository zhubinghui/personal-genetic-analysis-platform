import asyncio
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.samples import router as samples_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.reports import router as reports_router
from app.api.v1.oauth import router as oauth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.admin.knowledge import router as admin_knowledge_router
from app.api.v1.admin.users import router as admin_users_router
from app.api.v1.admin.settings import router as admin_settings_router
from app.api.v1.trends import router as trends_router
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.audit import AuditLog

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("服务启动", environment=settings.environment)
    yield
    logger.info("服务关闭")


app = FastAPI(
    title="个人基因抗衰老分析平台",
    version="0.1.0",
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url="/api/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 审计日志中间件 ──────────────────────────────────────────
@app.middleware("http")
async def audit_middleware(request: Request, call_next) -> Response:
    response = await call_next(request)

    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        asyncio.create_task(
            _write_audit_log(request, response.status_code)
        )

    return response


async def _write_audit_log(request: Request, status_code: int) -> None:
    try:
        # 从 Authorization header 提取 user_id（若已登录）
        user_id = None
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            from app.utils.auth import decode_access_token
            payload = decode_access_token(auth[7:])
            if payload:
                try:
                    user_id = uuid.UUID(payload["sub"])
                except (KeyError, ValueError):
                    pass

        async with AsyncSessionLocal() as db:
            db.add(AuditLog(
                user_id=user_id,
                action=f"{request.method} {request.url.path}",
                resource_type="http",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata_={"status_code": status_code},
            ))
            await db.commit()
    except Exception:
        pass  # 审计日志失败不应影响主流程


# ── 路由注册 ────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1")
app.include_router(oauth_router, prefix="/api/v1")
app.include_router(samples_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(admin_knowledge_router, prefix="/api/v1")
app.include_router(admin_users_router, prefix="/api/v1")
app.include_router(admin_settings_router, prefix="/api/v1")
app.include_router(trends_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


@app.get("/health", tags=["系统"])
async def health():
    return {"status": "ok", "version": "0.1.0"}
