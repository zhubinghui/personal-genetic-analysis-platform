"""
共享测试夹具（fixtures）

- 纯单元测试：直接 import 服务层，无需 DB
- 集成测试（API）：使用真实 PostgreSQL + pgvector，通过 httpx AsyncClient 调用 FastAPI
"""

import base64
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.utils.auth import create_access_token, hash_password


# ── 测试数据库引擎 ─────────────────────────────────────────

# CI 中由 GitHub Actions 服务容器提供; 本地由 Docker Compose 提供
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    settings.database_url,
)

_test_engine = create_async_engine(TEST_DB_URL, echo=False)
_TestSessionLocal = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False
)


# ── 数据库生命周期 ────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _setup_db():
    """整个测试会话只建/拆一次表。"""
    async with _test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest_asyncio.fixture
async def db(_setup_db) -> AsyncSession:
    """每个测试用例一个事务，测试结束后回滚。"""
    async with _TestSessionLocal() as session:
        yield session
        await session.rollback()


# ── FastAPI 测试客户端 ────────────────────────────────────

async def _override_get_db():
    async with _TestSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def client(_setup_db) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── 辅助 fixtures ─────────────────────────────────────────

@pytest.fixture
def encryption_key() -> bytes:
    """固定的 32 字节 AES-256 测试密钥。"""
    return base64.b64decode("dGVzdGtleTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNA==")


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    """创建普通测试用户。"""
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("TestPass123!"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    """创建管理员测试用户。"""
    user = User(
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("AdminPass123!"),
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def user_token(test_user: User) -> str:
    return create_access_token({"sub": str(test_user.id)})


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token({"sub": str(admin_user.id)})
