"""
FastAPI 后端侧的 Celery 任务发送客户端。
只发送任务，不导入 Worker 代码（Worker 在独立容器中）。
"""

from celery import Celery

from app.config import settings

_celery_client: Celery | None = None


def _get_client() -> Celery:
    global _celery_client
    if _celery_client is None:
        _celery_client = Celery(
            broker=settings.celery_broker_url,
            backend=settings.celery_result_backend,
        )
    return _celery_client


def send_analysis_task(job_id: str, sample_id: str) -> str:
    """发送分析任务到 Celery 队列，返回 celery_task_id"""
    client = _get_client()
    result = client.send_task(
        "worker.tasks.run_analysis",
        args=[job_id, sample_id],
        queue="analysis",
    )
    return result.id
