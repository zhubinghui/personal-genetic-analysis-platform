"""
同龄对标服务

实时计算用户分析结果在同年龄组人群中的百分位排名。
MVP 阶段使用全表扫描；用户量增大后可改为预计算。
"""

import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisJob, AnalysisResult
from app.models.sample import Sample
from app.schemas.trend import BenchmarkData, BenchmarkMetric

# 年龄组宽度（岁）
AGE_GROUP_WIDTH = 5
# 年龄组最低样本量，不足时回退到全人群
MIN_COHORT_SIZE = 5


def _age_group(age: int) -> tuple[int, int]:
    """返回 (下限, 上限) 如 (35, 39)。"""
    lower = (age // AGE_GROUP_WIDTH) * AGE_GROUP_WIDTH
    return lower, lower + AGE_GROUP_WIDTH - 1


def _age_group_label(age: int) -> str:
    lo, hi = _age_group(age)
    return f"{lo}-{hi}"


def _percentile_rank(user_value: float, all_values: list[float], lower_is_better: bool = True) -> float:
    """
    计算百分位排名（0~100）。
    lower_is_better=True 时：值越小排名越高（如 DunedinPACE）。
    """
    if not all_values:
        return 50.0
    count_better = sum(1 for v in all_values if (v > user_value if lower_is_better else v < user_value))
    count_equal = sum(1 for v in all_values if v == user_value)
    return round((count_better + 0.5 * count_equal) / len(all_values) * 100, 1)


def _stats(values: list[float]) -> tuple[float | None, float | None]:
    """计算均值和标准差。"""
    if not values:
        return None, None
    mean = sum(values) / len(values)
    if len(values) < 2:
        return round(mean, 3), None
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return round(mean, 3), round(math.sqrt(variance), 3)


async def compute_benchmark(
    db: AsyncSession,
    result: AnalysisResult,
) -> BenchmarkData | None:
    """
    计算单个分析结果在同龄人群中的百分位。
    结果为 None 时（无年龄或无时钟数据）返回 None。
    """
    age = result.chronological_age
    if age is None:
        return None

    age_lo, age_hi = _age_group(age)

    # 查询同龄组所有已完成结果
    cohort_query = (
        select(AnalysisResult)
        .join(AnalysisJob, AnalysisResult.job_id == AnalysisJob.id)
        .join(Sample, AnalysisResult.sample_id == Sample.id)
        .where(
            AnalysisJob.status == "completed",
            Sample.deleted_at.is_(None),
            AnalysisResult.chronological_age.isnot(None),
            AnalysisResult.chronological_age >= age_lo,
            AnalysisResult.chronological_age <= age_hi,
        )
    )

    cohort_rows = (await db.execute(cohort_query)).scalars().all()

    # 样本不足时回退到全人群
    age_group_label = _age_group_label(age)
    if len(cohort_rows) < MIN_COHORT_SIZE:
        all_query = (
            select(AnalysisResult)
            .join(AnalysisJob, AnalysisResult.job_id == AnalysisJob.id)
            .join(Sample, AnalysisResult.sample_id == Sample.id)
            .where(
                AnalysisJob.status == "completed",
                Sample.deleted_at.is_(None),
                AnalysisResult.chronological_age.isnot(None),
            )
        )
        cohort_rows = (await db.execute(all_query)).scalars().all()
        age_group_label = "全年龄段"

    if not cohort_rows:
        return None

    # 提取各指标值
    pace_values = [r.dunedinpace for r in cohort_rows if r.dunedinpace is not None]
    horvath_acc = [
        r.horvath_age - r.chronological_age
        for r in cohort_rows
        if r.horvath_age is not None and r.chronological_age is not None
    ]
    grim_acc = [
        r.grimage_age - r.chronological_age
        for r in cohort_rows
        if r.grimage_age is not None and r.chronological_age is not None
    ]
    pheno_acc = [
        r.phenoage_age - r.chronological_age
        for r in cohort_rows
        if r.phenoage_age is not None and r.chronological_age is not None
    ]

    # 计算用户百分位
    def _make_metric(
        user_val: float | None, cohort: list[float], lower_is_better: bool = True
    ) -> BenchmarkMetric:
        mean, std = _stats(cohort)
        pct = _percentile_rank(user_val, cohort, lower_is_better) if user_val is not None else None
        return BenchmarkMetric(value=user_val, percentile=pct, cohort_mean=mean, cohort_std=std)

    user_horvath_acc = (
        result.horvath_age - result.chronological_age
        if result.horvath_age is not None and result.chronological_age is not None
        else None
    )
    user_grim_acc = (
        result.grimage_age - result.chronological_age
        if result.grimage_age is not None and result.chronological_age is not None
        else None
    )
    user_pheno_acc = (
        result.phenoage_age - result.chronological_age
        if result.phenoage_age is not None and result.chronological_age is not None
        else None
    )

    return BenchmarkData(
        age_group=age_group_label,
        cohort_size=len(cohort_rows),
        dunedinpace=_make_metric(result.dunedinpace, pace_values, lower_is_better=True),
        horvath_acceleration=_make_metric(user_horvath_acc, horvath_acc, lower_is_better=True),
        grimage_acceleration=_make_metric(user_grim_acc, grim_acc, lower_is_better=True),
        phenoage_acceleration=_make_metric(user_pheno_acc, pheno_acc, lower_is_better=True),
    )
