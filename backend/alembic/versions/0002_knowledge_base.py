"""knowledge base: pgvector extension, knowledge tables, is_admin column

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    # ── 启用 pgvector 扩展 ────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── users 表：添加 is_admin 列 ─────────────────────────────
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
    )

    # ── knowledge_documents ───────────────────────────────────
    op.create_table(
        "knowledge_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("authors", sa.String(1000), nullable=True),
        sa.Column("journal", sa.String(500), nullable=True),
        sa.Column("published_year", sa.Integer(), nullable=True),
        sa.Column("doi", sa.String(255), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("file_key", sa.String(512), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_knowledge_documents_status", "knowledge_documents", ["status"])
    op.create_index(
        "ix_knowledge_documents_created_at", "knowledge_documents", ["created_at"]
    )

    # ── document_chunks ───────────────────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        # pgvector 向量列（384 维）
        sa.Column(
            "embedding",
            sa.TEXT(),  # 占位符；由 pgvector 处理实际类型
        ),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("chunk_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"
        ),
    )

    # 将 embedding 列类型改为真正的 vector 类型
    op.execute(
        f"ALTER TABLE document_chunks "
        f"ALTER COLUMN embedding TYPE vector({EMBEDDING_DIM}) "
        f"USING embedding::vector({EMBEDDING_DIM})"
    )

    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # HNSW 近似最近邻索引（余弦距离，适合语义搜索）
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.drop_table("document_chunks")
    op.drop_table("knowledge_documents")
    op.drop_column("users", "is_admin")
    op.execute("DROP EXTENSION IF EXISTS vector")
