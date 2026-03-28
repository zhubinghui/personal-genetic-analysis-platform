"""
知识库业务逻辑

功能：
  - 文档 CRUD（创建 / 查询 / 删除）
  - 后台异步处理（解析 + 嵌入）
  - pgvector 语义相似度搜索
"""

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import DocumentChunk, KnowledgeDocument
from app.schemas.knowledge import SearchResultChunk
from app.services.document_processor import parse_document
from app.services.embedding_service import embed_query, embed_texts

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ── 文档处理 ─────────────────────────────────────────────────

async def process_document_background(
    document_id: uuid.UUID,
    file_bytes: bytes,
    file_type: str,
    db_session_factory,
) -> None:
    """
    后台任务：解析文档 → 生成嵌入 → 写入 document_chunks。
    由 FastAPI BackgroundTasks 调用，使用独立数据库会话。
    """
    async with db_session_factory() as db:
        try:
            # 更新状态为 processing
            await db.execute(
                update(KnowledgeDocument)
                .where(KnowledgeDocument.id == document_id)
                .values(status="processing", error_message=None)
            )
            await db.commit()

            # 解析文档
            logger.info("开始解析文档 %s (类型: %s)", document_id, file_type)
            chunks = await asyncio.to_thread(parse_document, file_bytes, file_type)

            if not chunks:
                raise ValueError("文档中未提取到任何文本内容")

            # 批量生成嵌入向量（每批 64 条）
            batch_size = 64
            all_embeddings: list[list[float]] = []
            for i in range(0, len(chunks), batch_size):
                batch_texts = [c.text for c in chunks[i:i + batch_size]]
                batch_embs = await embed_texts(batch_texts)
                all_embeddings.extend(batch_embs)

            # 删除旧切片（重新处理时）
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )

            # 批量插入新切片
            db.add_all([
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.text,
                    embedding=embedding,
                    page_number=chunk.page_number,
                    chunk_metadata={"char_count": len(chunk.text)},
                )
                for chunk, embedding in zip(chunks, all_embeddings)
            ])

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
            # 确保即使 rollback 失败也能标记为 failed
            try:
                await db.rollback()
            except Exception:
                pass
            try:
                # 使用新的 session 确保状态更新成功
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

    # pgvector 余弦距离 = 1 - 余弦相似度
    # 使用 <=> 运算符（cosine_distance），结果越小越相似
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
