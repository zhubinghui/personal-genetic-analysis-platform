import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("samples.id", ondelete="CASCADE"), nullable=False, index=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="queued"  # queued/running/completed/failed
    )
    stage: Mapped[str | None] = mapped_column(
        String(50), nullable=True  # qc/normalization/clocks/reporting
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sample: Mapped["Sample"] = relationship("Sample", back_populates="analysis_jobs")  # noqa: F821
    result: Mapped["AnalysisResult | None"] = relationship(
        "AnalysisResult", back_populates="job", uselist=False
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False
    )
    sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("samples.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # QC 指标
    qc_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    n_probes_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_probes_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detection_p_failed_fraction: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 输入信息
    chronological_age: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 衰老时钟评分
    horvath_age: Mapped[float | None] = mapped_column(Float, nullable=True)
    grimage_age: Mapped[float | None] = mapped_column(Float, nullable=True)
    phenoage_age: Mapped[float | None] = mapped_column(Float, nullable=True)

    # DunedinPACE：衰老速率（1.0 = 人群平均，>1 = 加速）
    dunedinpace: Mapped[float | None] = mapped_column(Float, nullable=True)

    # DunedinPACE 19 维度分项评分（JSONB，结构见 analysis/pipeline/result_parser.py）
    dunedinpace_dimensions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 衍生指标
    biological_age_acceleration: Mapped[float | None] = mapped_column(Float, nullable=True)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="result")
