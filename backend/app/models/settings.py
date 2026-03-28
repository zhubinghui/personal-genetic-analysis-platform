"""
系统设置模型 — key-value 存储

用于管理员动态配置 LLM Provider、API Key 等运行时设置。
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    category: Mapped[str] = mapped_column(String(50), primary_key=True)   # "llm"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)        # "api_key"
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
