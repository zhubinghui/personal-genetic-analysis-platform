"""纵向对比 + 同龄对标 Pydantic 模式"""

import uuid
from datetime import datetime

from pydantic import BaseModel


# ── 纵向对比 ─────────────────────────────────────────────

class TrendPoint(BaseModel):
    sample_id: uuid.UUID
    job_id: uuid.UUID
    uploaded_at: datetime
    chronological_age: int | None
    horvath_age: float | None
    grimage_age: float | None
    phenoage_age: float | None
    dunedinpace: float | None
    biological_age_acceleration: float | None
    dimension_summary: dict[str, float | None]  # 9 系统平均得分


class TrendResponse(BaseModel):
    points: list[TrendPoint]
    total_samples: int


# ── 同龄对标 ─────────────────────────────────────────────

class BenchmarkMetric(BaseModel):
    value: float | None
    percentile: float | None  # 0~100，越高越好
    cohort_mean: float | None
    cohort_std: float | None


class BenchmarkData(BaseModel):
    age_group: str              # 如 "35-39"
    cohort_size: int            # 该年龄组样本数
    dunedinpace: BenchmarkMetric
    horvath_acceleration: BenchmarkMetric
    grimage_acceleration: BenchmarkMetric
    phenoage_acceleration: BenchmarkMetric
