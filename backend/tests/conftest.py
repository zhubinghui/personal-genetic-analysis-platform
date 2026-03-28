"""
共享测试夹具

策略：每个测试使用独立的 AsyncSession（不共享连接），
用 UUID 保证数据唯一性，避免 asyncpg 并发冲突。
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

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", settings.database_url)
_test_engine = create_async_engine(TEST_DB_URL, echo=False, pool_size=5, max_overflow=10)
_TestSession = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


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


# ── DB session（独立连接）──────────────────────────────────

@pytest_asyncio.fixture
async def db(_setup_db) -> AsyncSession:
    async with _TestSession() as session:
        yield session


# ── FastAPI 测试客户端 ────────────────────────────────────

@pytest_asyncio.fixture
async def client(_setup_db) -> AsyncClient:
    async def _override():
        async with _TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


# ── 辅助 fixtures ─────────────────────────────────────────

@pytest.fixture
def encryption_key() -> bytes:
    return base64.b64decode("dGVzdGtleTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNA==")


@pytest_asyncio.fixture
async def test_user(_setup_db) -> User:
    """创建普通用户并 commit（对所有 session 可见）。"""
    async with _TestSession() as session:
        user = User(
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPass123!"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def admin_user(_setup_db) -> User:
    """创建管理员用户并 commit（对所有 session 可见）。"""
    async with _TestSession() as session:
        user = User(
            email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("AdminPass123!"),
            is_admin=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def user_token(test_user: User) -> str:
    return create_access_token({"sub": str(test_user.id)})


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token({"sub": str(admin_user.id)})
