"""
知识库业务逻辑

架构：
  - 向量化使用独立进程池（ProcessPoolExecutor），完全绕过 GIL，真正 CPU 并行
  - 每个 worker 进程加载独立的嵌入模型实例，内存约 200MB/进程
  - API 查询在主进程事件循环中运行，与向量化零干扰
  - DB 写入操作回到主进程异步执行
"""

import asyncio
import logging
import os
import uuid
from concurrent.futures import ProcessPoolExecutor

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import DocumentChunk, KnowledgeDocument
from app.schemas.knowledge import SearchResultChunk
from app.services.document_processor import parse_document
from app.services.embedding_service import embed_query, embed_texts_sync

logger = logging.getLogger(__name__)

# 向量化专用进程池：
# - 独立进程，完全绕过 Python GIL，CPU 密集型任务真正并行
# - 默认 2 个 worker（每个进程加载独立的嵌入模型，内存约 200MB/进程）
# - 可通过环境变量 EMBEDDING_WORKERS 调整
EMBEDDING_WORKERS = int(os.environ.get("EMBEDDING_WORKERS", "2"))
_embedding_pool: ProcessPoolExecutor | None = None


def _get_embedding_pool() -> ProcessPoolExecutor:
    """懒初始化进程池（避免 fork 时机问题）。"""
    global _embedding_pool
    if _embedding_pool is None:
        _embedding_pool = ProcessPoolExecutor(max_workers=EMBEDDING_WORKERS)
        logger.info("向量化进程池启动: %d workers", EMBEDDING_WORKERS)
    return _embedding_pool


def _process_document_sync(
    file_bytes: bytes,
    file_type: str,
) -> tuple[list, list[list[float]]]:
    """
    同步执行：解析文档 + 生成嵌入（在独立线程中运行）。
    返回 (chunks, embeddings)，不涉及任何 DB 操作。
    """
    # 1. 解析文档
    chunks = parse_document(file_bytes, file_type)
    if not chunks:
        raise ValueError("文档中未提取到任何文本内容")

    # 2. 清洗文本（移除 PostgreSQL 不支持的 null 字节）
    for chunk in chunks:
        chunk.text = chunk.text.replace("\x00", "")

    # 3. 批量生成嵌入向量
    batch_size = 32
    all_embeddings: list[list[float]] = []
    for i in range(0, len(chunks), batch_size):
        batch_texts = [c.text for c in chunks[i:i + batch_size]]
        batch_embs = embed_texts_sync(batch_texts)
        all_embeddings.extend(batch_embs)

    return chunks, all_embeddings


async def process_document_background(
    document_id: uuid.UUID,
    file_bytes: bytes,
    file_type: str,
    db_session_factory,
) -> None:
    """
    后台任务：在专用线程池中解析+嵌入，完成后写入 DB。
    多个文档可并行处理（受线程池 worker 数限制），API 不受影响。
    """
    # 标记为 processing
    async with db_session_factory() as db:
        await db.execute(
            update(KnowledgeDocument)
            .where(KnowledgeDocument.id == document_id)
            .values(status="processing", error_message=None)
        )
        await db.commit()

    try:
        # 在专用进程池中执行 CPU 密集的解析+嵌入
        # 独立进程绕过 GIL，真正并行，完全不阻塞主进程事件循环
        loop = asyncio.get_event_loop()
        logger.info("文档 %s 开始向量化 (类型: %s)", document_id, file_type)
        chunks, all_embeddings = await loop.run_in_executor(
            _get_embedding_pool(),
            _process_document_sync,
            file_bytes,
            file_type,
        )

        # 写入 DB（回到异步）
        async with db_session_factory() as db:
            # 删除旧切片
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )

            # 分批插入
            insert_batch = 50
            for i in range(0, len(chunks), insert_batch):
                batch_c = chunks[i:i + insert_batch]
                batch_e = all_embeddings[i:i + insert_batch]
                db.add_all([
                    DocumentChunk(
                        document_id=document_id,
                        chunk_index=c.chunk_index,
                        chunk_text=c.text,
                        embedding=e,
                        page_number=c.page_number,
                        chunk_metadata={"char_count": len(c.text)},
                    )
                    for c, e in zip(batch_c, batch_e)
                ])
                await db.flush()

            # 更新状态
            await db.execute(
                update(KnowledgeDocument)
                .where(KnowledgeDocument.id == document_id)
                .values(status="ready", chunk_count=len(chunks), error_message=None)
            )
            await db.commit()

        logger.info("文档 %s 向量化完成，共 %d 个切片", document_id, len(chunks))

    except Exception as e:
        logger.error("文档 %s 向量化失败: %s", document_id, e)
        try:
            async with db_session_factory() as db2:
                await db2.execute(
                    update(KnowledgeDocument)
                    .where(KnowledgeDocument.id == document_id)
                    .values(status="failed", error_message=str(e)[:500])
                )
                await db2.commit()
        except Exception as e2:
            logger.error("文档 %s 状态更新也失败: %s", document_id, e2)


# ── 查询 ────────────────────────────────────────────────────

async def list_documents(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
) -> tuple[int, list[KnowledgeDocument]]:
    query = select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
    count_query = select(func.count()).select_from(KnowledgeDocument)

    if status:
        query = query.where(KnowledgeDocument.status == status)
        count_query = count_query.where(KnowledgeDocument.status == status)

    total = (await db.execute(count_query)).scalar_one()
    items = (await db.execute(query.offset(skip).limit(limit))).scalars().all()
    return total, list(items)


async def get_document(
    db: AsyncSession, document_id: uuid.UUID
) -> KnowledgeDocument | None:
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    )
    return result.scalar_one_or_none()


async def delete_document(db: AsyncSession, document_id: uuid.UUID) -> bool:
    """删除文档及其所有切片（级联删除）。"""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        return False
    await db.delete(doc)
    await db.commit()
    return True


# ── 语义搜索 ─────────────────────────────────────────────────

async def semantic_search(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.3,
) -> list[SearchResultChunk]:
    """
    使用 pgvector 余弦相似度进行语义搜索。
    只在 status='ready' 的文档切片中搜索。
    """
    query_embedding = await embed_query(query)

    distance_col = DocumentChunk.embedding.cosine_distance(query_embedding)

    stmt = (
        select(
            DocumentChunk,
            KnowledgeDocument.title.label("doc_title"),
            (1 - distance_col).label("score"),
        )
        .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
        .where(KnowledgeDocument.status == "ready")
        .where((1 - distance_col) >= score_threshold)
        .order_by(distance_col)
        .limit(top_k)
    )

    rows = (await db.execute(stmt)).all()

    return [
        SearchResultChunk(
            document_id=row.DocumentChunk.document_id,
            document_title=row.doc_title,
            chunk_index=row.DocumentChunk.chunk_index,
            chunk_text=row.DocumentChunk.chunk_text,
            page_number=row.DocumentChunk.page_number,
            score=round(float(row.score), 4),
        )
        for row in rows
    ]
