"""知识库管理 API 集成测试"""

import io

import pytest
from httpx import AsyncClient


def _make_txt_file(content: str = "Epigenetic aging and DNA methylation clocks.") -> tuple[str, bytes, str]:
    """返回 (field_name, file_bytes, filename)"""
    return ("file", io.BytesIO(content.encode()).read(), "test_paper.txt")


class TestKnowledgeUpload:
    async def test_upload_requires_admin(self, client: AsyncClient, user_token: str):
        """普通用户上传应返回 403。"""
        res = await client.post(
            "/api/v1/admin/knowledge",
            data={"title": "Test Paper"},
            files={"file": ("paper.txt", b"content", "text/plain")},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 403

    async def test_upload_no_auth(self, client: AsyncClient):
        """无认证上传应返回 403。"""
        res = await client.post(
            "/api/v1/admin/knowledge",
            data={"title": "Test"},
            files={"file": ("paper.txt", b"content", "text/plain")},
        )
        assert res.status_code == 403

    async def test_unsupported_file_type(self, client: AsyncClient, admin_token: str):
        """不支持的文件类型应返回 400。"""
        res = await client.post(
            "/api/v1/admin/knowledge",
            data={"title": "Bad File"},
            files={"file": ("paper.exe", b"\x00\x00", "application/octet-stream")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 400
        assert "不支持" in res.json()["detail"]


class TestKnowledgeList:
    async def test_list_requires_admin(self, client: AsyncClient, user_token: str):
        res = await client.get(
            "/api/v1/admin/knowledge",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 403

    async def test_list_empty(self, client: AsyncClient, admin_token: str):
        """空知识库应返回空列表。"""
        res = await client.get(
            "/api/v1/admin/knowledge",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)


class TestKnowledgeSearch:
    async def test_search_requires_admin(self, client: AsyncClient, user_token: str):
        res = await client.post(
            "/api/v1/admin/knowledge/search",
            json={"query": "aging", "top_k": 5},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 403

    async def test_search_empty_kb(self, client: AsyncClient, admin_token: str):
        """空知识库搜索应返回空结果而非报错。"""
        res = await client.post(
            "/api/v1/admin/knowledge/search",
            json={"query": "epigenetic aging", "top_k": 5},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "epigenetic aging"
        assert data["results"] == []
