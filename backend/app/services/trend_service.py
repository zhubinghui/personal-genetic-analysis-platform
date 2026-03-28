"""
纵向对比服务

查询用户所有已完成的分析结果，每个样本只取最新一次分析，按时间排序返回趋势数据。
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisJob, AnalysisResult
from app.models.sample import Sample
from app.schemas.trend import TrendPoint, TrendResponse


def _dimension_summary(dims: dict | None) -> dict[str, float | None]:
    """将 19 维度 JSONB 压缩为 9 系统平均得分。"""
    if not dims:
        return {}
    summary: dict[str, float | None] = {}
    for system, metrics in dims.items():
        if not isinstance(metrics, dict):
            continue
        values = [v for v in metrics.values() if v is not None]
        summary[system] = round(sum(values) / len(values), 3) if values else None
    return summary


async def get_user_trends(
    db: AsyncSession,
    pseudonym_id: uuid.UUID,
) -> TrendResponse:
    """
    获取用户所有已完成分析的时序趋势数据。
    每个样本只保留最新一次完成的分析（避免重复分析产生多个趋势点）。
    """
    # 子查询：每个 sample_id 的最新完成 job
    latest_job_subq = (
        select(
            AnalysisJob.sample_id,
            func.max(AnalysisJob.completed_at).label("max_completed"),
        )
        .where(AnalysisJob.status == "completed")
        .group_by(AnalysisJob.sample_id)
        .subquery()
    )

    stmt = (
        select(
            AnalysisResult,
            Sample.id.label("sample_id"),
            Sample.uploaded_at,
            AnalysisJob.id.label("job_id"),
        )
        .join(AnalysisJob, AnalysisResult.job_id == AnalysisJob.id)
        .join(Sample, AnalysisResult.sample_id == Sample.id)
        .join(
            latest_job_subq,
            (AnalysisJob.sample_id == latest_job_subq.c.sample_id)
            & (AnalysisJob.completed_at == latest_job_subq.c.max_completed),
        )
        .where(
            Sample.pseudonym_id == pseudonym_id,
            Sample.deleted_at.is_(None),
            AnalysisJob.status == "completed",
        )
        .order_by(Sample.uploaded_at.asc())
    )

    rows = (await db.execute(stmt)).all()

    points = [
        TrendPoint(
            sample_id=row.sample_id,
            job_id=row.job_id,
            uploaded_at=row.uploaded_at,
            chronological_age=row.AnalysisResult.chronological_age,
            horvath_age=row.AnalysisResult.horvath_age,
            grimage_age=row.AnalysisResult.grimage_age,
            phenoage_age=row.AnalysisResult.phenoage_age,
            dunedinpace=row.AnalysisResult.dunedinpace,
            biological_age_acceleration=row.AnalysisResult.biological_age_acceleration,
            dimension_summary=_dimension_summary(
                row.AnalysisResult.dunedinpace_dimensions
            ),
        )
        for row in rows
    ]

    return TrendResponse(points=points, total_samples=len(points))
