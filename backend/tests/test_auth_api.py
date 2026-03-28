"""认证 API 集成测试（连接到运行中的 FastAPI 服务）"""

import os
import uuid

import pytest
from httpx import AsyncClient


def _unique_email() -> str:
    return f"auth_test_{uuid.uuid4().hex[:8]}@example.com"


def _verify_email_sync(email: str) -> None:
    """直接在数据库中验证邮箱（测试用）。"""
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


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        email = _unique_email()
        res = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "StrongPass123!",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == email
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        email = _unique_email()
        res1 = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "StrongPass123!",
        })
        assert res1.status_code == 201
        res2 = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "AnotherPass123!",
        })
        assert res2.status_code == 400
        assert "已注册" in res2.json()["detail"]


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        email = _unique_email()
        await client.post("/api/v1/auth/register", json={"email": email, "password": "MyPass123!"})
        _verify_email_sync(email)  # 需先验证邮箱
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": "MyPass123!"})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_unverified_blocked(self, client: AsyncClient):
        """未验证邮箱的用户登录应返回 403。"""
        email = _unique_email()
        await client.post("/api/v1/auth/register", json={"email": email, "password": "MyPass123!"})
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": "MyPass123!"})
        assert res.status_code == 403
        assert "验证邮箱" in res.json()["detail"]

    async def test_login_wrong_password(self, client: AsyncClient):
        email = _unique_email()
        await client.post("/api/v1/auth/register", json={"email": email, "password": "CorrectPass!"})
        _verify_email_sync(email)
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass!"})
        assert res.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        res = await client.post("/api/v1/auth/login", json={
            "email": f"nobody_{uuid.uuid4().hex[:8]}@example.com",
            "password": "whatever",
        })
        assert res.status_code == 401


class TestMe:
    async def test_me_with_token(self, client: AsyncClient, test_user: dict, user_token: str):
        res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 200
        assert res.json()["email"] == test_user["email"]

    async def test_me_no_token(self, client: AsyncClient):
        res = await client.get("/api/v1/auth/me")
        assert res.status_code == 403

    async def test_me_invalid_token(self, client: AsyncClient):
        res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert res.status_code == 401
