import os

from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "genetic_analysis",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["worker.tasks"],
)

celery_app.conf.update(
    # 序列化
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # 队列路由
    task_routes={
        "worker.tasks.run_analysis": {"queue": "analysis"},
    },

    # 任务跟踪
    task_track_started=True,

    # 内存保护：每次只预取 1 个任务（分析任务内存密集）
    worker_prefetch_multiplier=1,

    # 超时（2 小时硬限制，110 分钟软超时）
    task_time_limit=7200,
    task_soft_time_limit=6600,

    # 崩溃恢复：任务完成后再 ack，崩溃则重新入队
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # 重试策略
    task_max_retries=2,
    task_default_retry_delay=300,  # 5 分钟后重试
)
