"""
Mock Celery Worker — 生成模拟分析结果，用于 UI 测试
使用同步 psycopg2 避免 asyncpg 并发问题
"""
import json
import os
import random
import time
import uuid

import psycopg2
import psycopg2.extras
from celery import Celery

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6380/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6380/1")
DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://app_user:dev_password_2026@localhost:5432/genetic_platform",
)

celery_app = Celery("mock_worker", broker=REDIS_URL, backend=RESULT_BACKEND)
celery_app.conf.task_queues = {"analysis": {}}
celery_app.conf.task_default_queue = "analysis"
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.acks_late = True
celery_app.conf.broker_connection_retry_on_startup = True


def get_conn():
    return psycopg2.connect(DATABASE_URL_SYNC)


def mock_dimensions(pace: float) -> dict:
    systems = {
        "cardiovascular": ["systolic_bp", "diastolic_bp", "pulse_rate", "hdl_cholesterol", "total_cholesterol"],
        "metabolic": ["hba1c", "bmi", "fasting_glucose", "triglycerides"],
        "renal": ["creatinine", "urea_nitrogen"],
        "pulmonary": ["fev1", "fvc"],
        "immune": ["crp", "white_blood_cells"],
        "periodontal": ["dental_health"],
        "cognitive": ["cognitive_score"],
        "physical": ["grip_strength", "balance"],
    }
    result = {}
    for system, indicators in systems.items():
        result[system] = {ind: round(max(0.5, min(2.0, pace + random.gauss(0, 0.09))), 3) for ind in indicators}
    return result


@celery_app.task(name="worker.tasks.run_analysis", bind=True, max_retries=1)
def run_analysis(self, job_id: str, sample_id: str):
    print(f"[mock] 收到任务 job={job_id[:8]}…")
    conn = get_conn()
    cur = conn.cursor()

    try:
        # 1. 标记为 running/qc
        cur.execute(
            "UPDATE analysis_jobs SET status='running', stage='qc', started_at=now() WHERE id=%s",
            (job_id,),
        )
        conn.commit()
        print(f"[mock] {job_id[:8]}… QC 阶段")
        time.sleep(3)

        # 2. 标记为 clocks 阶段
        cur.execute("UPDATE analysis_jobs SET stage='clocks' WHERE id=%s", (job_id,))
        conn.commit()
        print(f"[mock] {job_id[:8]}… 时钟计算阶段")
        time.sleep(4)

        # 3. 获取实际年龄
        cur.execute("SELECT chronological_age FROM samples WHERE id=%s", (sample_id,))
        row = cur.fetchone()
        chron_age = row[0] if row and row[0] else 45

        # 4. 生成模拟结果
        pace = round(random.gauss(1.05, 0.12), 3)
        horvath = round(chron_age + random.gauss(2.5, 4), 1)
        grimage = round(chron_age + random.gauss(3.0, 5), 1)
        phenoage = round(chron_age + random.gauss(1.5, 3.5), 1)
        accel = round(((horvath + grimage + phenoage) / 3) - chron_age, 2)
        dims = mock_dimensions(pace)

        # 5. 写入结果
        result_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO analysis_results (
                id, job_id, sample_id,
                qc_passed, n_probes_before, n_probes_after, detection_p_failed_fraction,
                chronological_age, horvath_age, grimage_age, phenoage_age,
                dunedinpace, dunedinpace_dimensions, biological_age_acceleration
            ) VALUES (%s, %s, %s, true, 862000, 851432, 0.012, %s, %s, %s, %s, %s, %s, %s)
            """,
            (result_id, job_id, sample_id, chron_age, horvath, grimage, phenoage,
             pace, json.dumps(dims), accel),
        )

        # 6. 标记 completed
        cur.execute(
            "UPDATE analysis_jobs SET status='completed', stage='done', completed_at=now() WHERE id=%s",
            (job_id,),
        )
        conn.commit()
        print(f"[mock] {job_id[:8]}… ✅ completed — pace={pace}, accel={accel:+.1f}yr")

    except Exception as e:
        conn.rollback()
        cur.execute(
            "UPDATE analysis_jobs SET status='failed', error_message=%s WHERE id=%s",
            (str(e), job_id),
        )
        conn.commit()
        print(f"[mock] {job_id[:8]}… ❌ failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    print(f"启动 Mock Celery Worker — broker={REDIS_URL}")
    celery_app.worker_main(
        argv=["worker", "--loglevel=info", "-Q", "analysis", "--concurrency=1"]
    )
