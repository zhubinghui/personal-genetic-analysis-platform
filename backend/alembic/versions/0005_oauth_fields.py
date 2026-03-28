"""add oauth fields to users

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("oauth_provider", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("oauth_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(512), nullable=True))
    # password_hash 改为 nullable（OAuth 用户无密码）
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    # (oauth_provider, oauth_id) 组合唯一索引
    op.create_index("ix_users_oauth", "users", ["oauth_provider", "oauth_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_oauth")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "oauth_id")
    op.drop_column("users", "oauth_provider")
