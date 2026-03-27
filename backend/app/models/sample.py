import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sample(Base):
    __tablename__ = "samples"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 只存 pseudonym_id，不存 user.id（隐私隔离核心）
    pseudonym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.pseudonym_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    array_type: Mapped[str] = mapped_column(
        String(20), nullable=False  # 'EPIC', '450K', 'beta_csv'
    )
    upload_status: Mapped[str] = mapped_column(
        String(20), default="pending"  # pending/validated/failed
    )

    # 加密后在 MinIO 中的对象路径
    file_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # 明文 SHA-256（加密前计算，用于完整性校验）
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # 用于 GrimAge 等需要年龄信息的时钟
    chronological_age: Mapped[int | None] = mapped_column(Integer, nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # GDPR 软删除：设置后立即删除 MinIO 对象，30 天后硬删除数据库记录
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[pseudonym_id],
        primaryjoin="Sample.pseudonym_id == User.pseudonym_id",
        back_populates="samples",
    )
    analysis_jobs: Mapped[list["AnalysisJob"]] = relationship(  # noqa: F821
        "AnalysisJob", back_populates="sample"
    )
