"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("pseudonym_id", postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("consent_version", sa.String(20), nullable=True),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_unique_constraint("uq_users_pseudonym_id", "users", ["pseudonym_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_pseudonym_id", "users", ["pseudonym_id"])

    # ── samples ─────────────────────────────────────────────────
    op.create_table(
        "samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("pseudonym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("array_type", sa.String(20), nullable=False),
        sa.Column("upload_status", sa.String(20), server_default="pending"),
        sa.Column("file_key", sa.String(512), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("chronological_age", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pseudonym_id"], ["users.pseudonym_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_samples_pseudonym_id", "samples", ["pseudonym_id"])

    # ── analysis_jobs ────────────────────────────────────────────
    op.create_table(
        "analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("stage", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analysis_jobs_sample_id", "analysis_jobs", ["sample_id"])

    # ── analysis_results ─────────────────────────────────────────
    op.create_table(
        "analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qc_passed", sa.Boolean(), nullable=True),
        sa.Column("n_probes_before", sa.Integer(), nullable=True),
        sa.Column("n_probes_after", sa.Integer(), nullable=True),
        sa.Column("detection_p_failed_fraction", sa.Float(), nullable=True),
        sa.Column("chronological_age", sa.Integer(), nullable=True),
        sa.Column("horvath_age", sa.Float(), nullable=True),
        sa.Column("grimage_age", sa.Float(), nullable=True),
        sa.Column("phenoage_age", sa.Float(), nullable=True),
        sa.Column("dunedinpace", sa.Float(), nullable=True),
        sa.Column("dunedinpace_dimensions", postgresql.JSONB(), nullable=True),
        sa.Column("biological_age_acceleration", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analysis_results_sample_id", "analysis_results", ["sample_id"])

    # ── audit_logs ────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("analysis_results")
    op.drop_table("analysis_jobs")
    op.drop_table("samples")
    op.drop_table("users")
