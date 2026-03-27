"""
管理员知识库 API

端点：
  POST   /admin/knowledge/upload        — 上传文献文件
  GET    /admin/knowledge               — 分页列出文献
  GET    /admin/knowledge/{doc_id}      — 获取文献详情
  DELETE /admin/knowledge/{doc_id}      — 删除文献
  POST   /admin/knowledge/{doc_id}/reprocess — 重新处理（重新嵌入）
  POST   /admin/knowledge/search        — 语义搜索测试
"""

import uuid
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_admin_user
from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.models.knowledge import KnowledgeDocument
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeDocumentList,
    KnowledgeDocumentOut,
    SearchRequest,
    SearchResponse,
)
from app.services.knowledge_service import (
    delete_document,
    get_document,
    list_documents,
    process_document_background,
    semantic_search,
)
from app.services.storage_service import StorageService, get_storage

router = APIRouter(prefix="/admin/knowledge", tags=["管理员-知识库"])

ALLOWED_TYPES = {"pdf", "docx", "txt", "md"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _get_file_ext(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return parts[-1].lower() if len(parts) == 2 else ""


# ── 上传文献 ──────────────────────────────────────────────────

@router.post("", response_model=KnowledgeDocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    title: Annotated[str, Form(min_length=1, max_length=500)],
    description: Annotated[str | None, Form()] = None,
    authors: Annotated[str | None, Form()] = None,
    journal: Annotated[str | None, Form()] = None,
    published_year: Annotated[int | None, Form(ge=1900, le=2100)] = None,
    doi: Annotated[str | None, Form()] = None,
    tags: Annotated[str | None, Form()] = None,  # 逗号分隔
    current_admin: Annotated[User, Depends(get_admin_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    storage: Annotated[StorageService, Depends(get_storage)] = None,
):
    """上传文献文件（PDF / DOCX / TXT），并启动后台向量化处理。"""
    file_ext = _get_file_ext(file.filename or "")
    if file_ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型 .{file_ext}，仅支持 PDF / DOCX / TXT",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="文件大小超过 50 MB 限制",
        )

    # 存储到 MinIO（knowledge 专用 bucket，无加密——文献是公开文献）
    doc_id = uuid.uuid4()
    object_key = f"knowledge/{doc_id}/{file.filename}"
    import io
    import asyncio
    await asyncio.to_thread(
        storage.client.put_object,
        settings.minio_bucket_knowledge,
        object_key,
        io.BytesIO(file_bytes),
        len(file_bytes),
        content_type=file.content_type or "application/octet-stream",
    )

    # 解析 tags
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()] or None

    # 创建 DB 记录
    doc = KnowledgeDocument(
        id=doc_id,
        title=title,
        description=description,
        authors=authors,
        journal=journal,
        published_year=published_year,
        doi=doi,
        tags=tag_list,
        file_key=object_key,
        file_name=file.filename or f"document.{file_ext}",
        file_type=file_ext,
        file_size_bytes=len(file_bytes),
        status="pending",
        uploaded_by=current_admin.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 后台处理：解析 + 嵌入
    background_tasks.add_task(
        process_document_background,
        doc_id,
        file_bytes,
        file_ext,
        AsyncSessionLocal,
    )

    return doc


# ── 列出文献 ──────────────────────────────────────────────────

@router.get("", response_model=KnowledgeDocumentList)
async def list_knowledge_documents(
    skip: int = 0,
    limit: int = 20,
    status_filter: Literal["pending", "processing", "ready", "failed"] | None = None,
    _: Annotated[User, Depends(get_admin_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    total, items = await list_documents(db, skip=skip, limit=min(limit, 100), status=status_filter)
    return KnowledgeDocumentList(total=total, items=items)


# ── 文献详情 ──────────────────────────────────────────────────

@router.get("/{doc_id}", response_model=KnowledgeDocumentOut)
async def get_knowledge_document(
    doc_id: uuid.UUID,
    _: Annotated[User, Depends(get_admin_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    doc = await get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文献不存在")
    return doc


# ── 删除文献 ──────────────────────────────────────────────────

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_document(
    doc_id: uuid.UUID,
    _: Annotated[User, Depends(get_admin_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    storage: Annotated[StorageService, Depends(get_storage)] = None,
):
    doc = await get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文献不存在")

    # 删除 MinIO 文件
    import asyncio
    try:
        await asyncio.to_thread(
            storage.client.remove_object,
            settings.minio_bucket_knowledge,
            doc.file_key,
        )
    except Exception:
        pass  # MinIO 文件不存在时忽略

    await delete_document(db, doc_id)


# ── 重新处理 ──────────────────────────────────────────────────

@router.post("/{doc_id}/reprocess", response_model=KnowledgeDocumentOut)
async def reprocess_document(
    doc_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    _: Annotated[User, Depends(get_admin_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    storage: Annotated[StorageService, Depends(get_storage)] = None,
):
    """重新下载并嵌入文献（用于模型升级后重建索引）。"""
    doc = await get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文献不存在")
    if doc.status == "processing":
        raise HTTPException(status_code=409, detail="文献正在处理中，请稍后再试")

    # 从 MinIO 下载原文件
    import asyncio
    response = await asyncio.to_thread(
        storage.client.get_object,
        settings.minio_bucket_knowledge,
        doc.file_key,
    )
    file_bytes = response.read()
    response.close()
    response.release_conn()

    background_tasks.add_task(
        process_document_background,
        doc_id,
        file_bytes,
        doc.file_type,
        AsyncSessionLocal,
    )

    doc.status = "pending"
    await db.commit()
    await db.refresh(doc)
    return doc


# ── 语义搜索 ──────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse)
async def knowledge_search(
    request: SearchRequest,
    _: Annotated[User, Depends(get_admin_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """在向量数据库中执行语义相似度搜索。"""
    results = await semantic_search(
        db,
        query=request.query,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
    )
    return SearchResponse(query=request.query, results=results)
