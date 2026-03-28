"""knowledge_documents 表添加 file_hash 防重字段

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knowledge_documents",
        sa.Column("file_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_knowledge_documents_file_hash",
        "knowledge_documents",
        ["file_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_documents_file_hash", table_name="knowledge_documents")
    op.drop_column("knowledge_documents", "file_hash")
