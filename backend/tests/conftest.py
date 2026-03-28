"""
共享测试夹具

策略：
- 单元测试：使用 db fixture (session-scoped engine, 与 pytest 事件循环对齐)
- 集成测试：使用 client fixture 连接到 localhost:8000 真实服务
  (Docker 容器内 backend 已运行; CI 中由 service container 提供)
"""

import base64
import os
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.user import User
from app.utils.auth import create_access_token, hash_password

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://app_user:changeme@postgres:5432/genetic_platform",
    ),
)

API_BASE = os.environ.get("TEST_API_BASE", "http://localhost:8000")


# ── DB engine（session 级别，与 pytest 事件循环一致） ─────

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False, pool_size=5, max_overflow=10)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _session_factory(_db_engine):
    return async_sessionmaker(_db_engine, class_=AsyncSession, expire_on_commit=False)


# ── DB session（单元测试 + RAG 测试用）────────────────────

@pytest_asyncio.fixture
async def db(_session_factory) -> AsyncSession:
    async with _session_factory() as session:
        yield session


# ── HTTP 测试客户端（集成测试用，连真实服务）────────────────

@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """连接到运行中的 FastAPI 服务器（Docker 内 localhost:8000）。"""
    async with AsyncClient(base_url=API_BASE) as c:
        yield c


# ── 辅助 fixtures ─────────────────────────────────────────

@pytest.fixture
def encryption_key() -> bytes:
    return base64.b64decode("dGVzdGtleTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNA==")


def _verify_user_sync(email: str) -> None:
    """用 psycopg2 同步设置 email_verified=true。"""
    import psycopg2
    sync_url = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql://app_user:changeme@postgres:5432/genetic_platform",
    )
    conn = psycopg2.connect(sync_url)
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET email_verified=true, email_verified_at=NOW() WHERE email=%s", (email,))
        conn.commit()
    finally:
        conn.close()


@pytest_asyncio.fixture
async def test_user(client: AsyncClient) -> dict:
    """通过 API 创建已验证的普通测试用户。"""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    res = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
    })
    assert res.status_code == 201, f"注册失败: {res.text}"
    _verify_user_sync(email)
    return {"email": email, "password": password, **res.json()}


@pytest_asyncio.fixture
async def admin_user(client: AsyncClient) -> dict:
    """通过 API 注册 + psycopg2 同步提权为管理员。"""
    import psycopg2

    email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "AdminPass123!"

    # 1. 通过 API 注册普通用户
    res = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, f"注册管理员失败: {res.text}"

    # 2. 用同步 psycopg2 设置 is_admin=true + email_verified=true
    import psycopg2
    sync_url = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql://app_user:changeme@postgres:5432/genetic_platform",
    )
    conn = psycopg2.connect(sync_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_admin=true, email_verified=true, email_verified_at=NOW() WHERE email=%s",
                (email,),
            )
        conn.commit()
    finally:
        conn.close()

    return {"email": email, "password": password, **res.json()}


@pytest_asyncio.fixture
async def user_token(client: AsyncClient, test_user: dict) -> str:
    """通过 API 登录获取 token。"""
    res = await client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"],
    })
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user: dict) -> str:
    """管理员登录获取 token。"""
    res = await client.post("/api/v1/auth/login", json={
        "email": admin_user["email"],
        "password": admin_user["password"],
    })
    assert res.status_code == 200
    return res.json()["access_token"]


# ── 测试结束后清理测试用户 ────────────────────────

def pytest_sessionfinish(session, exitstatus):
    """测试会话结束后，清理所有 @example.com 测试用户。"""
    import psycopg2
    sync_url = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql://app_user:changeme@postgres:5432/genetic_platform",
    )
    try:
        conn = psycopg2.connect(sync_url)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_logs WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%%@example.com')")
            cur.execute("DELETE FROM samples WHERE pseudonym_id IN (SELECT pseudonym_id FROM users WHERE email LIKE '%%@example.com')")
            cur.execute("DELETE FROM users WHERE email LIKE '%%@example.com'")
            deleted = cur.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            print(f"\n[conftest cleanup] 清理了 {deleted} 个测试用户")
    except Exception:
        pass  # CI 环境可能无数据库，静默跳过
