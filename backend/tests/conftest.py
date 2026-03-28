"""
共享测试夹具

关键：engine 在 session 级 fixture 内创建，确保与 pytest-asyncio 使用同一事件循环。
"""

import base64
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.utils.auth import create_access_token, hash_password

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://app_user:changeme@postgres:5432/genetic_platform",
    ),
)


# ── 数据库 engine + session factory（session 级别，与事件循环一致）──

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False, pool_size=5, max_overflow=10)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _session_factory(_db_engine):
    return async_sessionmaker(_db_engine, class_=AsyncSession, expire_on_commit=False)


# ── DB session ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def db(_session_factory) -> AsyncSession:
    async with _session_factory() as session:
        yield session


# ── FastAPI 测试客户端 ────────────────────────────────────

@pytest_asyncio.fixture
async def client(_session_factory) -> AsyncClient:
    async def _override():
        async with _session_factory() as session:
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
async def test_user(_session_factory) -> User:
    async with _session_factory() as session:
        user = User(
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPass123!"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def admin_user(_session_factory) -> User:
    async with _session_factory() as session:
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
