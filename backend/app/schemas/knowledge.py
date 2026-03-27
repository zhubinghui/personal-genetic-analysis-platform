"""知识库 Pydantic 模式"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── 文档 ─────────────────────────────────────────────────────

class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    authors: str | None = None
    journal: str | None = None
    published_year: int | None = Field(None, ge=1900, le=2100)
    doi: str | None = None
    tags: list[str] | None = None


class KnowledgeDocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    authors: str | None
    journal: str | None
    published_year: int | None
    doi: str | None
    tags: list[str] | None
    file_name: str
    file_type: str
    file_size_bytes: int | None
    status: Literal["pending", "processing", "ready", "failed"]
    error_message: str | None
    chunk_count: int
    uploaded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeDocumentList(BaseModel):
    total: int
    items: list[KnowledgeDocumentOut]


# ── 语义搜索 ─────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.3, ge=0.0, le=1.0)


class SearchResultChunk(BaseModel):
    document_id: uuid.UUID
    document_title: str
    chunk_index: int
    chunk_text: str
    page_number: int | None
    score: float  # 余弦相似度（0~1，越高越相关）


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultChunk]
