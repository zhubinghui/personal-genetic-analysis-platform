"""
共享测试夹具（fixtures）

关键设计：集成测试中 `db` 和 `client` 共享同一个数据库连接和外层事务，
测试结束后整体回滚，确保测试隔离。
"""

import base64
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.utils.auth import create_access_token, hash_password


# ── 测试数据库引擎 ─────────────────────────────────────────

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", settings.database_url)
_test_engine = create_async_engine(TEST_DB_URL, echo=False, pool_size=5)


# ── 数据库生命周期（session 级别） ─────────────────────────

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


# ── 每个测试共享一个连接 + 外层事务 → 结束后回滚 ─────────

@pytest_asyncio.fixture
async def _db_connection(_setup_db):
    """为每个测试用例创建一个独立连接 + 外层事务。"""
    async with _test_engine.connect() as conn:
        trans = await conn.begin()
        yield conn
        await trans.rollback()


@pytest_asyncio.fixture
async def db(_db_connection: AsyncConnection) -> AsyncSession:
    """
    提供一个绑定到测试连接的 AsyncSession。
    内部 commit() 会变成 savepoint（不会真正提交外层事务）。
    """
    session = AsyncSession(bind=_db_connection, expire_on_commit=False)
    # 使 session.commit() 创建 savepoint 而非提交外层事务
    @event.listens_for(session.sync_session, "after_transaction_end")
    def _restart_savepoint(session_sync, transaction):
        if transaction.nested and not transaction._parent.nested:
            session_sync.begin_nested()

    yield session
    await session.close()


@pytest_asyncio.fixture
async def client(_db_connection: AsyncConnection, _setup_db) -> AsyncClient:
    """
    httpx 测试客户端。API 内部的 get_db 被覆盖为返回与 `db` 同一连接的 session，
    确保 fixture 创建的数据对 API 可见。
    """
    async def _override_get_db():
        session = AsyncSession(bind=_db_connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


# ── 辅助 fixtures ─────────────────────────────────────────

@pytest.fixture
def encryption_key() -> bytes:
    """固定的 32 字节 AES-256 测试密钥。"""
    return base64.b64decode("dGVzdGtleTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNA==")


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    """创建普通测试用户（对 client 可见）。"""
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("TestPass123!"),
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    """创建管理员测试用户（对 client 可见）。"""
    user = User(
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("AdminPass123!"),
        is_admin=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
def user_token(test_user: User) -> str:
    return create_access_token({"sub": str(test_user.id)})


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token({"sub": str(admin_user.id)})
