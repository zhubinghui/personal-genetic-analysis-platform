"""
知识库业务逻辑

功能：
  - 文档 CRUD（创建 / 查询 / 删除）
  - 后台异步处理（独立线程池，不阻塞 API）
  - pgvector 语义相似度搜索
"""

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import DocumentChunk, KnowledgeDocument
from app.schemas.knowledge import SearchResultChunk
from app.services.document_processor import parse_document
from app.services.embedding_service import embed_query, embed_texts_sync

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# 向量化专用线程池（2 个 worker，不占用 API 线程）
_embedding_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embed")

# 任务队列：保证一次只处理一个文档（避免资源争抢）
_processing_semaphore = asyncio.Semaphore(1)


# ── 文档处理 ─────────────────────────────────────────────────

async def process_document_background(
    document_id: uuid.UUID,
    file_bytes: bytes,
    file_type: str,
    db_session_factory,
) -> None:
    """
    后台任务：解析文档 → 生成嵌入 → 写入 document_chunks。
    使用信号量确保同一时间只处理一个文档，避免阻塞 API。
    """
    async with _processing_semaphore:
        async with db_session_factory() as db:
            try:
                # 更新状态为 processing
                await db.execute(
                    update(KnowledgeDocument)
                    .where(KnowledgeDocument.id == document_id)
                    .values(status="processing", error_message=None)
                )
                await db.commit()

                # 在专用线程池中解析文档（不阻塞 API 线程池）
                logger.info("开始解析文档 %s (类型: %s)", document_id, file_type)
                loop = asyncio.get_event_loop()
                chunks = await loop.run_in_executor(
                    _embedding_executor, parse_document, file_bytes, file_type
                )

                if not chunks:
                    raise ValueError("文档中未提取到任何文本内容")

                # 清洗文本：移除 null 字节（PostgreSQL 不支持 \x00）
                for chunk in chunks:
                    chunk.text = chunk.text.replace("\x00", "")

                # 在专用线程池中批量生成嵌入向量
                batch_size = 32  # 减小批次避免长时间占用
                all_embeddings: list[list[float]] = []
                for i in range(0, len(chunks), batch_size):
                    batch_texts = [c.text for c in chunks[i:i + batch_size]]
                    batch_embs = await loop.run_in_executor(
                        _embedding_executor, embed_texts_sync, batch_texts
                    )
                    all_embeddings.extend(batch_embs)
                    # 每批次后让出事件循环，让 API 请求得以处理
                    await asyncio.sleep(0)

                # 删除旧切片（重新处理时）
                await db.execute(
                    delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
                )

                # 分批插入（避免单条 SQL 过大）
                insert_batch = 50
                for i in range(0, len(chunks), insert_batch):
                    batch_chunks = chunks[i:i + insert_batch]
                    batch_embs = all_embeddings[i:i + insert_batch]
                    db.add_all([
                        DocumentChunk(
                            document_id=document_id,
                            chunk_index=chunk.chunk_index,
                            chunk_text=chunk.text,
                            embedding=embedding,
                            page_number=chunk.page_number,
                            chunk_metadata={"char_count": len(chunk.text)},
                        )
                        for chunk, embedding in zip(batch_chunks, batch_embs)
                    ])
                    await db.flush()
                    await asyncio.sleep(0)  # 让出事件循环

                # 更新文档状态
                await db.execute(
                    update(KnowledgeDocument)
                    .where(KnowledgeDocument.id == document_id)
                    .values(status="ready", chunk_count=len(chunks), error_message=None)
                )
                await db.commit()
                logger.info("文档 %s 处理完成，共 %d 个切片", document_id, len(chunks))

            except Exception as e:
                logger.error("文档 %s 处理失败: %s", document_id, e)
                try:
                    await db.rollback()
                except Exception:
                    pass
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
