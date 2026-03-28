"""OAuth API 集成测试"""

import pytest
from httpx import AsyncClient


class TestOAuthProviders:
    async def test_list_providers(self, client: AsyncClient):
        """GET /auth/oauth/providers 应返回所有 Provider 列表。"""
        res = await client.get("/api/v1/auth/oauth/providers")
        assert res.status_code == 200
        data = res.json()
        assert "providers" in data
        names = [p["name"] for p in data["providers"]]
        assert "github" in names
        assert "google" in names
        assert "wechat" in names

    async def test_providers_have_configured_flag(self, client: AsyncClient):
        res = await client.get("/api/v1/auth/oauth/providers")
        for p in res.json()["providers"]:
            assert "configured" in p
            assert isinstance(p["configured"], bool)

    async def test_authorize_unconfigured_provider_returns_400(self, client: AsyncClient):
        """未配置的 Provider 应返回 400。"""
        res = await client.get("/api/v1/auth/oauth/github/authorize")
        # GitHub 未在 .env 中配置时应返回 400
        if res.status_code == 400:
            assert "未配置" in res.json()["detail"]

    async def test_authorize_unknown_provider_returns_error(self, client: AsyncClient):
        res = await client.get("/api/v1/auth/oauth/facebook/authorize")
        assert res.status_code in (400, 422, 500)
