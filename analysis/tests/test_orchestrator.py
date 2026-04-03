"""Integration tests for analysis/pipeline/orchestrator.py — mocked R scripts and DB."""

import json
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def _make_mock_sample(file_key="test/sample/beta.csv.enc", age=40):
    """Create a mock Sample ORM object."""
    sample = MagicMock()
    sample.id = uuid.uuid4()
    sample.file_key = file_key
    sample.array_type = "EPIC"
    sample.chronological_age = age
    sample.upload_status = "processing"
    return sample


def _make_mock_job():
    """Create a mock AnalysisJob ORM object."""
    job = MagicMock()
    job.id = uuid.uuid4()
    job.status = "queued"
    job.stage = None
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    return job


@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    storage.download_decrypted = AsyncMock(return_value=b"fake,csv,data\n0.5,0.3,0.8")
    return storage


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def r_outputs():
    """All R script outputs for a successful run."""
    return {
        "qc_normalize.R": _load_fixture("mock_qc_passed.json"),
        "horvath_clock.R": _load_fixture("mock_horvath.json"),
        "grimage.R": _load_fixture("mock_grimage.json"),
        "phenoage.R": _load_fixture("mock_phenoage.json"),
        "dunedinpace.R": _load_fixture("mock_dunedinpace.json"),
    }


def _mock_run_r_script(outputs: dict):
    """Return a side_effect function that routes by script name."""
    def side_effect(script_name, input_args, **kwargs):
        if script_name in outputs:
            return outputs[script_name]
        raise FileNotFoundError(f"No mock for {script_name}")
    return side_effect


def _setup_mock_db(mock_db, job, sample):
    """Configure mock_db.execute to return job or sample depending on call order.

    The orchestrator's call sequence through db.execute is:
      1. _update_job (select AnalysisJob) — returns job
      2. select(Sample) in run() — returns sample
      3+ _update_job calls — return job
    """
    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 2:
            result.scalar_one_or_none.return_value = sample
        else:
            result.scalar_one_or_none.return_value = job
        return result

    mock_db.execute = mock_execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()


def _make_mock_model_class(name="MockModel"):
    """Create a mock that works as both a class (with .id attribute access) and
    a callable constructor. Needed because the orchestrator does both
    ``select(AnalysisJob).where(AnalysisJob.id == ...)`` and
    ``AnalysisResult(job_id=..., ...)``.
    """
    cls = MagicMock(name=name)
    # Ensure class-level attribute access for .id, .status etc. works
    # (MagicMock instances already support arbitrary attribute access)
    return cls


def _make_sys_modules_patch():
    """Create the sys.modules patch dict for deferred imports in the orchestrator."""
    mock_analysis_job_cls = _make_mock_model_class("AnalysisJob")
    mock_analysis_result_cls = _make_mock_model_class("AnalysisResult")
    mock_sample_cls = _make_mock_model_class("Sample")

    mock_settings = MagicMock()
    mock_settings.minio_bucket_idat = "idat-raw"

    mock_analysis_mod = MagicMock()
    mock_analysis_mod.AnalysisJob = mock_analysis_job_cls
    mock_analysis_mod.AnalysisResult = mock_analysis_result_cls

    mock_sample_mod = MagicMock()
    mock_sample_mod.Sample = mock_sample_cls

    mock_config_mod = MagicMock()
    mock_config_mod.settings = mock_settings

    # sqlalchemy.orm is already importable, but we need selectinload to not
    # cause issues — it's imported but the return value is never used in a way
    # that matters for our mocks, so the real import is fine.

    return {
        "app": MagicMock(),
        "app.models": MagicMock(),
        "app.models.analysis": mock_analysis_mod,
        "app.models.sample": mock_sample_mod,
        "app.config": mock_config_mod,
    }


class TestOrchestratorSuccess:
    @patch("pipeline.orchestrator.select")
    @patch("pipeline.orchestrator.run_r_script")
    @pytest.mark.asyncio
    async def test_full_pipeline_success(
        self, mock_r, mock_select, mock_storage, mock_db, r_outputs
    ):
        """Full successful pipeline: QC pass + 4 clocks + result persistence."""
        mock_r.side_effect = _mock_run_r_script(r_outputs)

        sample = _make_mock_sample()
        job = _make_mock_job()
        _setup_mock_db(mock_db, job, sample)

        with patch.dict("sys.modules", _make_sys_modules_patch()):
            from pipeline.orchestrator import AnalysisPipeline
            pipeline = AnalysisPipeline(mock_storage, mock_db)
            result = await pipeline.run(str(job.id), str(sample.id))

        assert result.qc.qc_passed is True
        assert result.clocks.horvath_age == 43.7
        assert result.clocks.grimage_age == 46.2
        assert result.clocks.phenoage_age == 41.5
        assert result.clocks.dunedinpace == 1.032
        assert result.biological_age_acceleration is not None
        # acceleration = horvath_age - chronological_age = 43.7 - 40 = 3.7
        assert result.biological_age_acceleration == 3.7
        # QC (1) + 4 clocks = 5 R script calls
        assert mock_r.call_count == 5


class TestOrchestratorQCFailure:
    @patch("pipeline.orchestrator.select")
    @patch("pipeline.orchestrator.run_r_script")
    @pytest.mark.asyncio
    async def test_qc_failure_early_exit(
        self, mock_r, mock_select, mock_storage, mock_db
    ):
        """When QC fails, pipeline should return early without running clocks."""
        qc_failed = _load_fixture("mock_qc_failed.json")
        mock_r.return_value = qc_failed

        sample = _make_mock_sample()
        job = _make_mock_job()
        _setup_mock_db(mock_db, job, sample)

        with patch.dict("sys.modules", _make_sys_modules_patch()):
            from pipeline.orchestrator import AnalysisPipeline
            pipeline = AnalysisPipeline(mock_storage, mock_db)
            result = await pipeline.run(str(job.id), str(sample.id))

        assert result.qc.qc_passed is False
        assert result.clocks.horvath_age is None
        assert result.clocks.dunedinpace is None
        # Only QC was called, no clock scripts
        assert mock_r.call_count == 1
        # Job should be marked as failed
        assert job.status == "failed"


class TestOrchestratorClockFailure:
    @patch("pipeline.orchestrator.select")
    @patch("pipeline.orchestrator.run_r_script")
    @pytest.mark.asyncio
    async def test_clock_error_marks_job_failed(
        self, mock_r, mock_select, mock_storage, mock_db
    ):
        """When a clock R script fails, the job should be marked as failed."""
        qc_passed = _load_fixture("mock_qc_passed.json")

        def failing_r(script_name, input_args, **kwargs):
            if script_name == "qc_normalize.R":
                return qc_passed
            if script_name == "horvath_clock.R":
                from pipeline.r_bridge import RScriptError
                raise RScriptError("horvath_clock.R", "segfault", 139)
            # Other clocks return normally — but horvath failure will propagate
            return _load_fixture(
                f"mock_{script_name.replace('.R', '').replace('_clock', '')}.json"
            )

        mock_r.side_effect = failing_r

        sample = _make_mock_sample()
        job = _make_mock_job()
        _setup_mock_db(mock_db, job, sample)

        with patch.dict("sys.modules", _make_sys_modules_patch()):
            from pipeline.orchestrator import AnalysisPipeline
            pipeline = AnalysisPipeline(mock_storage, mock_db)

            with pytest.raises(Exception):
                await pipeline.run(str(job.id), str(sample.id))

        assert job.status == "failed"
        assert job.error_message is not None
        assert "衰老时钟计算失败" in job.error_message
