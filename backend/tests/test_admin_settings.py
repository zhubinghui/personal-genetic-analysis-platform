"""管理员系统设置 API 集成测试"""

import pytest
from httpx import AsyncClient


class TestLLMSettings:
    async def test_get_settings_requires_admin(self, client: AsyncClient, user_token: str):
        res = await client.get(
            "/api/v1/admin/settings/llm",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 403

    async def test_get_settings_as_admin(self, client: AsyncClient, admin_token: str):
        res = await client.get(
            "/api/v1/admin/settings/llm",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "provider" in data
        assert "api_key_masked" in data
        assert "available_providers" in data
        assert isinstance(data["available_providers"], list)

    async def test_update_settings_requires_admin(self, client: AsyncClient, user_token: str):
        res = await client.put(
            "/api/v1/admin/settings/llm",
            json={"provider": "claude", "api_key": "sk-test"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 403

    async def test_update_settings_as_admin(self, client: AsyncClient, admin_token: str):
        res = await client.put(
            "/api/v1/admin/settings/llm",
            json={"provider": "deepseek", "api_key": "sk-test-key-12345", "model": "deepseek-chat"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        assert "保存" in res.json()["message"]

        # 验证保存后读取
        get_res = await client.get(
            "/api/v1/admin/settings/llm",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_res.json()["provider"] == "deepseek"
        assert "sk-test-k" in get_res.json()["api_key_masked"]

    async def test_test_connection_no_config(self, client: AsyncClient, admin_token: str):
        """未配置时测试连接应返回 400。"""
        # 先清空配置
        await client.put(
            "/api/v1/admin/settings/llm",
            json={"provider": "", "api_key": ""},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        res = await client.post(
            "/api/v1/admin/settings/llm/test",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 400
        assert "未配置" in res.json()["detail"]


class TestChatEndpoint:
    async def test_chat_requires_auth(self, client: AsyncClient):
        res = await client.post("/api/v1/chat", json={"query": "test"})
        assert res.status_code == 403

    async def test_chat_no_llm_returns_503(self, client: AsyncClient, user_token: str):
        """LLM 未配置时 chat 应返回 503。"""
        res = await client.post(
            "/api/v1/chat",
            json={"query": "什么是 DunedinPACE?"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 503
        assert "未配置" in res.json()["detail"]
