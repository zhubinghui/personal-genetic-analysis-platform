"""认证 API 集成测试"""

import pytest
from httpx import AsyncClient


@pytest.fixture
def unique_email():
    import uuid
    return f"auth_test_{uuid.uuid4().hex[:8]}@example.com"


class TestRegister:
    async def test_register_success(self, client: AsyncClient, unique_email: str):
        res = await client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "StrongPass123!",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == unique_email
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient, unique_email: str):
        await client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "StrongPass123!",
        })
        res = await client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "AnotherPass123!",
        })
        assert res.status_code == 400
        assert "已注册" in res.json()["detail"]

    async def test_register_invalid_email(self, client: AsyncClient):
        res = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "Pass123!",
        })
        assert res.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, unique_email: str):
        await client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "MyPass123!",
        })
        res = await client.post("/api/v1/auth/login", json={
            "email": unique_email,
            "password": "MyPass123!",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_login_wrong_password(self, client: AsyncClient, unique_email: str):
        await client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "password": "CorrectPass!",
        })
        res = await client.post("/api/v1/auth/login", json={
            "email": unique_email,
            "password": "WrongPass!",
        })
        assert res.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        res = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "whatever",
        })
        assert res.status_code == 401


class TestMe:
    async def test_me_with_token(self, client: AsyncClient, test_user, user_token: str):
        res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 200
        assert res.json()["email"] == test_user.email

    async def test_me_no_token(self, client: AsyncClient):
        res = await client.get("/api/v1/auth/me")
        assert res.status_code == 403  # HTTPBearer returns 403 when missing

    async def test_me_invalid_token(self, client: AsyncClient):
        res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert res.status_code == 401
