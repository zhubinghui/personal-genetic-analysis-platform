"""
Celery 分析任务定义

task_acks_late=True：任务执行完成后才 ack，崩溃时自动重回队列
max_retries=2：最多重试 2 次，间隔 5 分钟
"""

import asyncio
import os
import sys

import structlog

from worker.celery_app import celery_app

# 将 analysis/ 加入 Python 路径，使 pipeline 模块可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = structlog.get_logger()


@celery_app.task(
    name="worker.tasks.run_analysis",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    acks_late=True,
)
def run_analysis(self, job_id: str, sample_id: str) -> dict:
    """
    主分析任务。
    在独立子进程中运行（Celery worker），通过 asyncio.run 调用异步编排器。
    """
    logger.info("开始分析任务", job_id=job_id, sample_id=sample_id)
    try:
        result = asyncio.run(_run_pipeline(job_id, sample_id))
        logger.info("分析任务完成", job_id=job_id)
        return {"status": "completed", "job_id": job_id}
    except Exception as exc:
        logger.error("分析任务异常，准备重试", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


async def _run_pipeline(job_id: str, sample_id: str) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from pipeline.orchestrator import AnalysisPipeline
    from pipeline.storage_adapter import get_storage_service

    # 在 Worker 容器中创建独立的数据库连接
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://app_user:changeme@postgres:5432/genetic_platform",
    )
    engine = create_async_engine(database_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as db:
        storage = get_storage_service()
        pipeline = AnalysisPipeline(storage, db)
        await pipeline.run(job_id, sample_id)

    await engine.dispose()
