"""
分析流水线编排器

执行顺序：
1. 从 MinIO 下载并解密样本文件
2. 写入临时目录（R 脚本需要文件路径）
3. 运行 QC + 归一化（qc_normalize.R）
4. 并行运行 4 个衰老时钟（ThreadPoolExecutor）
5. 解析并持久化结果到 PostgreSQL
6. 更新任务状态
"""

import asyncio
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.r_bridge import RScriptError, run_r_script
from pipeline.result_parser import (
    AnalysisPipelineResult,
    compute_acceleration,
    parse_clock_results,
    parse_qc_result,
)

logger = structlog.get_logger()


class AnalysisPipeline:
    def __init__(self, storage_service, db: AsyncSession) -> None:
        self.storage = storage_service
        self.db = db

    async def run(self, job_id: str, sample_id: str) -> AnalysisPipelineResult:
        from sqlalchemy.orm import selectinload

        # 延迟导入避免循环依赖
        from app.models.analysis import AnalysisJob, AnalysisResult  # type: ignore
        from app.models.sample import Sample  # type: ignore
        from app.config import settings  # type: ignore

        job_uuid = uuid.UUID(job_id)
        sample_uuid = uuid.UUID(sample_id)

        # ── Stage 1: 标记任务为运行中 ───────────────────────────
        await self._update_job(job_uuid, status="running", stage="qc", started=True)

        # ── Stage 2: 获取样本信息 ────────────────────────────────
        res = await self.db.execute(select(Sample).where(Sample.id == sample_uuid))
        sample = res.scalar_one_or_none()
        if sample is None:
            await self._fail_job(job_uuid, f"样本不存在: {sample_id}")
            raise ValueError(f"Sample not found: {sample_id}")

        # ── Stage 3: 下载解密，写入临时目录 ──────────────────────
        with tempfile.TemporaryDirectory(prefix="genetic_analysis_") as tmpdir:
            input_args = await self._prepare_input_files(sample, tmpdir, settings)
            input_args["output_dir"] = tmpdir  # R 脚本把 beta 矩阵存到此目录

            # ── Stage 4: QC + 归一化 ─────────────────────────────
            logger.info("开始 QC 归一化", job_id=job_id)
            qc_raw = run_r_script("qc_normalize.R", input_args)
            qc = parse_qc_result(qc_raw)

            if not qc.qc_passed:
                await self._fail_job(job_uuid, qc.error or "QC 失败")
                return AnalysisPipelineResult(qc=qc)

            # ── Stage 5: 并行运行 4 个时钟 ───────────────────────
            await self._update_job(job_uuid, stage="clocks")
            logger.info("开始并行衰老时钟计算", job_id=job_id)

            beta_path = qc.beta_matrix_path
            clock_args = {"beta_matrix_path": beta_path}
            grimage_args = {
                **clock_args,
                "chronological_age": sample.chronological_age or 40,
            }

            try:
                with ThreadPoolExecutor(max_workers=4) as pool:
                    fut_horvath    = pool.submit(run_r_script, "horvath_clock.R", clock_args)
                    fut_grimage    = pool.submit(run_r_script, "grimage.R", grimage_args)
                    fut_phenoage   = pool.submit(run_r_script, "phenoage.R", clock_args)
                    fut_dunedinpace = pool.submit(run_r_script, "dunedinpace.R", clock_args)

                    horvath_raw     = fut_horvath.result()
                    grimage_raw     = fut_grimage.result()
                    phenoage_raw    = fut_phenoage.result()
                    dunedinpace_raw = fut_dunedinpace.result()

                clocks = parse_clock_results(
                    horvath_raw, grimage_raw, phenoage_raw, dunedinpace_raw
                )
                accel = compute_acceleration(clocks.horvath_age, sample.chronological_age)
            except Exception as e:
                error_msg = f"衰老时钟计算失败: {type(e).__name__}: {e}"
                await self._fail_job(job_uuid, error_msg)
                raise

        # ── Stage 6: 持久化结果 ──────────────────────────────────
        await self._update_job(job_uuid, stage="reporting")
        res_obj = AnalysisResult(
            job_id=job_uuid,
            sample_id=sample_uuid,
            qc_passed=qc.qc_passed,
            n_probes_before=qc.n_probes_before,
            n_probes_after=qc.n_probes_after,
            detection_p_failed_fraction=qc.detection_p_failed_fraction,
            chronological_age=sample.chronological_age,
            horvath_age=clocks.horvath_age,
            grimage_age=clocks.grimage_age,
            phenoage_age=clocks.phenoage_age,
            dunedinpace=clocks.dunedinpace,
            dunedinpace_dimensions=clocks.dunedinpace_dimensions,
            biological_age_acceleration=accel,
        )
        self.db.add(res_obj)

        # 更新 sample 状态
        sample.upload_status = "completed"
        await self._update_job(job_uuid, status="completed", stage="completed", completed=True)
        await self.db.commit()

        logger.info(
            "分析完成",
            job_id=job_id,
            dunedinpace=clocks.dunedinpace,
            horvath_age=clocks.horvath_age,
            acceleration=accel,
        )

        return AnalysisPipelineResult(
            qc=qc,
            clocks=clocks,
            biological_age_acceleration=accel,
        )

    async def _prepare_input_files(self, sample, tmpdir: str, settings) -> dict:
        """下载解密样本文件，写入临时目录，返回 R 脚本输入参数"""
        file_key = sample.file_key

        if "|" in file_key:
            # IDAT 模式：红绿双文件
            red_key, grn_key = file_key.split("|", 1)
            red_bytes = await self.storage.download_decrypted(
                red_key, settings.minio_bucket_idat
            )
            grn_bytes = await self.storage.download_decrypted(
                grn_key, settings.minio_bucket_idat
            )
            # minfi 要求文件名以 _Red.idat 和 _Grn.idat 结尾且在同一目录
            base = os.path.join(tmpdir, "sample")
            red_path = base + "_Red.idat"
            grn_path = base + "_Grn.idat"
            Path(red_path).write_bytes(red_bytes)
            Path(grn_path).write_bytes(grn_bytes)
            return {
                "array_type": sample.array_type,
                "red_idat_path": red_path,
                "grn_idat_path": grn_path,
            }
        else:
            # beta CSV 模式
            csv_bytes = await self.storage.download_decrypted(
                file_key, settings.minio_bucket_idat
            )
            csv_path = os.path.join(tmpdir, "beta_matrix.csv")
            Path(csv_path).write_bytes(csv_bytes)
            return {
                "array_type": sample.array_type,
                "beta_csv_path": csv_path,
            }

    async def _update_job(
        self,
        job_id: uuid.UUID,
        status: str | None = None,
        stage: str | None = None,
        started: bool = False,
        completed: bool = False,
    ) -> None:
        from app.models.analysis import AnalysisJob  # type: ignore
        res = await self.db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
        job = res.scalar_one_or_none()
        if job is None:
            return
        if status:
            job.status = status
        if stage:
            job.stage = stage
        if started:
            job.started_at = datetime.now(timezone.utc)
        if completed:
            job.completed_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def _fail_job(self, job_id: uuid.UUID, error_message: str) -> None:
        from app.models.analysis import AnalysisJob  # type: ignore
        res = await self.db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
        job = res.scalar_one_or_none()
        if job:
            job.status = "failed"
            job.error_message = error_message
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
        logger.error("分析任务失败", job_id=str(job_id), error=error_message)
