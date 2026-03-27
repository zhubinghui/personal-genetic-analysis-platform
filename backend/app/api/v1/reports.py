import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.analysis import AnalysisJob
from app.models.sample import Sample
from app.models.user import User
from app.services.report_service import ReportService
from app.services.storage_service import StorageService, get_storage

router = APIRouter(prefix="/reports", tags=["报告"])


async def _verify_job_ownership(
    job_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> AnalysisJob:
    result = await db.execute(
        select(AnalysisJob)
        .join(Sample, AnalysisJob.sample_id == Sample.id)
        .where(
            AnalysisJob.id == job_id,
            Sample.pseudonym_id == current_user.pseudonym_id,
            AnalysisJob.status == "completed",
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="报告不存在或分析尚未完成")
    return job


@router.get("/{job_id}")
async def get_report(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage)],
) -> dict:
    await _verify_job_ownership(job_id, current_user, db)
    svc = ReportService(storage)
    report = await svc.generate(job_id, db)

    # 将推荐转换为可序列化格式
    return {
        "job_id": report.job_id,
        "generated_at": report.generated_at,
        "summary": report.summary,
        "clocks": {
            "horvath_age": report.clocks.horvath_age,
            "grimage_age": report.clocks.grimage_age,
            "phenoage_age": report.clocks.phenoage_age,
            "dunedinpace": report.clocks.dunedinpace,
            "chronological_age": report.clocks.chronological_age,
            "biological_age_acceleration": report.clocks.biological_age_acceleration,
        },
        "dimensions": report.dimensions,
        "recommendations": [
            {
                "dimension": r.dimension,
                "dimension_score": r.dimension_score,
                "priority": r.priority,
                "title": r.title,
                "summary": r.summary,
                "evidence_level": r.evidence_level,
                "pmids": r.pmids,
                "pubmed_urls": r.pubmed_urls,
                "category": r.category,
                "timeframe_weeks": r.timeframe_weeks,
            }
            for r in report.recommendations
        ],
        "qc_summary": {
            "qc_passed": report.qc_summary.qc_passed,
            "n_probes_before": report.qc_summary.n_probes_before,
            "n_probes_after": report.qc_summary.n_probes_after,
        },
        "pdf_available": report.pdf_available,
    }


@router.get("/{job_id}/pdf")
async def download_report_pdf(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage)],
) -> StreamingResponse:
    """流式传输 PDF 报告（解密后直接传输，不落本地磁盘）"""
    job = await _verify_job_ownership(job_id, current_user, db)

    # 获取 pseudonym_id
    result = await db.execute(select(Sample).where(Sample.id == job.sample_id))
    sample = result.scalar_one_or_none()
    if sample is None:
        raise HTTPException(status_code=404, detail="样本不存在")

    pdf_key = f"{sample.pseudonym_id}/{sample.id}/report_{job_id}.pdf.enc"

    try:
        pdf_bytes = await storage.download_decrypted(pdf_key, settings.minio_bucket_reports)
    except Exception:
        # PDF 不存在则重新生成
        svc = ReportService(storage)
        report = await svc.generate(job_id, db)
        if not report.pdf_available:
            raise HTTPException(status_code=500, detail="PDF 生成失败")
        pdf_bytes = await storage.download_decrypted(pdf_key, settings.minio_bucket_reports)

    import io
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="aging_report_{job_id}.pdf"'},
    )
