import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.analysis import AnalysisJob, AnalysisResult
from app.models.sample import Sample
from app.models.user import User
from app.schemas.analysis import AnalysisResultOut, JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["分析任务"])


async def _get_user_job(
    job_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> AnalysisJob:
    """获取属于当前用户的任务（通过 pseudonym_id 验权）"""
    result = await db.execute(
        select(AnalysisJob)
        .join(Sample, AnalysisJob.sample_id == Sample.id)
        .where(
            AnalysisJob.id == job_id,
            Sample.pseudonym_id == current_user.pseudonym_id,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisJob:
    return await _get_user_job(job_id, current_user, db)


@router.get("/{job_id}/result", response_model=AnalysisResultOut)
async def get_job_result(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisResult:
    job = await _get_user_job(job_id, current_user, db)
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态：{job.status}")

    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.job_id == job_id)
    )
    ar = result.scalar_one_or_none()
    if ar is None:
        raise HTTPException(status_code=404, detail="结果数据不存在")
    return ar
