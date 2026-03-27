"""
样本上传 API

端点：
  POST /samples/upload/idat       — 上传 IDAT 文件对（Red + Grn）
  POST /samples/upload/beta-csv   — 上传 beta 值矩阵 CSV
  GET  /samples                   — 列出当前用户的样本
  DELETE /samples/{sample_id}     — 删除样本（GDPR 删除权）
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_consented_user, get_current_user
from app.config import settings
from app.database import get_db
from app.models.analysis import AnalysisJob
from app.models.audit import AuditLog
from app.models.sample import Sample
from app.models.user import User
from app.schemas.sample import SampleOut, SampleUploadResponse
from app.services.file_validator import FileValidator
from app.services.storage_service import StorageService, get_storage
from app.utils.pseudonymization import get_pseudonym_id

router = APIRouter(prefix="/samples", tags=["样本"])

# 单文件最大 500MB
MAX_FILE_SIZE = 500 * 1024 * 1024

validator = FileValidator()


async def _read_upload(file: UploadFile, label: str) -> bytes:
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"{label} 文件过大（最大 500MB）",
        )
    return data


async def _create_job(sample_id: uuid.UUID, db: AsyncSession) -> AnalysisJob:
    job = AnalysisJob(sample_id=sample_id)
    db.add(job)
    await db.flush()
    return job


def _enqueue_analysis(job_id: uuid.UUID, sample_id: uuid.UUID) -> str:
    """发送 Celery 任务，返回 celery_task_id"""
    from app.workers.celery_client import send_analysis_task
    return send_analysis_task(str(job_id), str(sample_id))


# ── POST /upload/idat ────────────────────────────────────────────────────────
@router.post(
    "/upload/idat",
    response_model=SampleUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_idat(
    red_channel: UploadFile,
    grn_channel: UploadFile,
    array_type: Annotated[Literal["EPIC", "450K"], Form()],
    chronological_age: Annotated[int, Form()],
    request: Request,
    current_user: Annotated[User, Depends(get_consented_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage)],
) -> SampleUploadResponse:
    if not (1 <= chronological_age <= 120):
        raise HTTPException(status_code=422, detail="年龄须在 1-120 之间")

    # 读取文件
    red_bytes = await _read_upload(red_channel, "Red channel")
    grn_bytes = await _read_upload(grn_channel, "Grn channel")

    # 格式验证
    val = validator.validate_idat_pair(red_bytes, grn_bytes)
    if not val.valid:
        raise HTTPException(status_code=422, detail=val.error)

    pseudonym_id = get_pseudonym_id(current_user)

    # 创建样本记录
    sample = Sample(
        pseudonym_id=pseudonym_id,
        array_type=array_type,
        upload_status="pending",
        chronological_age=chronological_age,
    )
    db.add(sample)
    await db.flush()

    # 加密上传（Red + Grn）
    red_key, red_hash = await storage.upload_encrypted(
        pseudonym_id, sample.id, red_bytes, "Red.idat",
        settings.minio_bucket_idat,
    )
    grn_key, _ = await storage.upload_encrypted(
        pseudonym_id, sample.id, grn_bytes, "Grn.idat",
        settings.minio_bucket_idat,
    )

    # 存储键格式："{red_key}|{grn_key}"
    sample.file_key = f"{red_key}|{grn_key}"
    sample.file_hash = red_hash
    sample.file_size_bytes = len(red_bytes) + len(grn_bytes)
    sample.upload_status = "validated"

    # 创建分析任务
    job = await _create_job(sample.id, db)

    # 入队 Celery
    try:
        celery_task_id = _enqueue_analysis(job.id, sample.id)
        job.celery_task_id = celery_task_id
    except Exception:
        job.status = "queued"  # 保持 queued，由定时任务补偿

    db.add(AuditLog(
        user_id=current_user.id,
        action="SAMPLE_UPLOAD_IDAT",
        resource_type="sample",
        resource_id=sample.id,
        ip_address=request.client.host if request.client else None,
        metadata_={"array_type": array_type, "probe_count": val.probe_count},
    ))

    await db.commit()

    return SampleUploadResponse(
        sample_id=sample.id,
        job_id=job.id,
        array_type=array_type,
        status="queued",
        message="文件上传成功，分析任务已入队",
    )


# ── POST /upload/beta-csv ────────────────────────────────────────────────────
@router.post(
    "/upload/beta-csv",
    response_model=SampleUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_beta_csv(
    beta_csv: UploadFile,
    array_type: Annotated[Literal["EPIC", "450K"], Form()],
    chronological_age: Annotated[int, Form()],
    request: Request,
    current_user: Annotated[User, Depends(get_consented_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage)],
) -> SampleUploadResponse:
    if not (1 <= chronological_age <= 120):
        raise HTTPException(status_code=422, detail="年龄须在 1-120 之间")

    csv_bytes = await _read_upload(beta_csv, "Beta CSV")

    val = validator.validate_beta_csv(csv_bytes)
    if not val.valid:
        raise HTTPException(status_code=422, detail=val.error)

    pseudonym_id = get_pseudonym_id(current_user)

    sample = Sample(
        pseudonym_id=pseudonym_id,
        array_type=array_type,
        upload_status="pending",
        chronological_age=chronological_age,
    )
    db.add(sample)
    await db.flush()

    file_key, file_hash = await storage.upload_encrypted(
        pseudonym_id, sample.id, csv_bytes, "beta_matrix.csv",
        settings.minio_bucket_idat,
    )
    sample.file_key = file_key
    sample.file_hash = file_hash
    sample.file_size_bytes = len(csv_bytes)
    sample.upload_status = "validated"

    job = await _create_job(sample.id, db)

    try:
        celery_task_id = _enqueue_analysis(job.id, sample.id)
        job.celery_task_id = celery_task_id
    except Exception:
        job.status = "queued"

    db.add(AuditLog(
        user_id=current_user.id,
        action="SAMPLE_UPLOAD_BETA_CSV",
        resource_type="sample",
        resource_id=sample.id,
        ip_address=request.client.host if request.client else None,
    ))

    await db.commit()

    return SampleUploadResponse(
        sample_id=sample.id,
        job_id=job.id,
        array_type=array_type,
        status="queued",
        message="文件上传成功，分析任务已入队",
    )


# ── GET /samples ─────────────────────────────────────────────────────────────
@router.get("", response_model=list[SampleOut])
async def list_samples(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SampleOut]:
    result = await db.execute(
        select(Sample)
        .options(selectinload(Sample.analysis_jobs))
        .where(
            Sample.pseudonym_id == current_user.pseudonym_id,
            Sample.deleted_at.is_(None),
        )
        .order_by(Sample.uploaded_at.desc())
    )
    samples = list(result.scalars().all())
    out = []
    for s in samples:
        latest_job = max(s.analysis_jobs, key=lambda j: j.created_at, default=None)
        out.append(SampleOut(
            id=s.id,
            array_type=s.array_type,
            upload_status=s.upload_status,
            chronological_age=s.chronological_age,
            uploaded_at=s.uploaded_at,
            deleted_at=s.deleted_at,
            latest_job_id=latest_job.id if latest_job else None,
            latest_job_status=latest_job.status if latest_job else None,
        ))
    return out


# ── DELETE /samples/{sample_id} ──────────────────────────────────────────────
@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(
    sample_id: uuid.UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage)],
) -> None:
    result = await db.execute(
        select(Sample).where(
            Sample.id == sample_id,
            Sample.pseudonym_id == current_user.pseudonym_id,
            Sample.deleted_at.is_(None),
        )
    )
    sample = result.scalar_one_or_none()
    if sample is None:
        raise HTTPException(status_code=404, detail="样本不存在")

    # 立即删除 MinIO 对象
    if sample.file_key:
        for key in sample.file_key.split("|"):
            await storage.delete_object(key, settings.minio_bucket_idat)

    # 软删除
    sample.deleted_at = datetime.now(timezone.utc)

    db.add(AuditLog(
        user_id=current_user.id,
        action="SAMPLE_DELETE",
        resource_type="sample",
        resource_id=sample.id,
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()
