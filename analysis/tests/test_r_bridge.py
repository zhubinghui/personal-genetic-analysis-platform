"""Tests for analysis/pipeline/r_bridge.py — mocked subprocess calls."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.r_bridge import run_r_script, RScriptError, SCRIPTS_DIR


@pytest.fixture
def fake_r_script(tmp_path):
    """Create a fake R script file so the existence check passes."""
    script = tmp_path / "test_script.R"
    script.write_text("# fake")
    return script


class TestRunRScript:
    @patch("pipeline.r_bridge.SCRIPTS_DIR")
    @patch("subprocess.run")
    def test_success_returns_parsed_json(self, mock_run, mock_scripts_dir, tmp_path):
        script_file = tmp_path / "horvath_clock.R"
        script_file.write_text("# fake")
        mock_scripts_dir.__truediv__ = lambda self, name: script_file

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"horvath_age": 43.7}',
            stderr="",
        )

        result = run_r_script("horvath_clock.R", {"beta_matrix_path": "/tmp/beta.rds"})
        assert result == {"horvath_age": 43.7}

    def test_script_not_found_raises(self):
        with pytest.raises(FileNotFoundError, match="R 脚本不存在"):
            run_r_script("nonexistent_script.R", {})

    @patch("pipeline.r_bridge.SCRIPTS_DIR")
    @patch("subprocess.run")
    def test_nonzero_exit_raises_rscript_error(self, mock_run, mock_scripts_dir, tmp_path):
        script_file = tmp_path / "bad_script.R"
        script_file.write_text("# fake")
        mock_scripts_dir.__truediv__ = lambda self, name: script_file

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error in library(nonexistent): there is no package called 'nonexistent'",
        )

        with pytest.raises(RScriptError) as exc_info:
            run_r_script("bad_script.R", {})

        assert exc_info.value.returncode == 1
        assert "nonexistent" in exc_info.value.stderr

    @patch("pipeline.r_bridge.SCRIPTS_DIR")
    @patch("subprocess.run")
    def test_empty_stdout_raises_value_error(self, mock_run, mock_scripts_dir, tmp_path):
        script_file = tmp_path / "empty_output.R"
        script_file.write_text("# fake")
        mock_scripts_dir.__truediv__ = lambda self, name: script_file

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        with pytest.raises(ValueError, match="没有输出任何内容"):
            run_r_script("empty_output.R", {})

    @patch("pipeline.r_bridge.SCRIPTS_DIR")
    @patch("subprocess.run")
    def test_invalid_json_raises_value_error(self, mock_run, mock_scripts_dir, tmp_path):
        script_file = tmp_path / "bad_json.R"
        script_file.write_text("# fake")
        mock_scripts_dir.__truediv__ = lambda self, name: script_file

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="not valid json {{{",
            stderr="",
        )

        with pytest.raises(ValueError, match="无法解析为 JSON"):
            run_r_script("bad_json.R", {})

    @patch("pipeline.r_bridge.SCRIPTS_DIR")
    @patch("subprocess.run")
    def test_timeout_raises_timeout_error(self, mock_run, mock_scripts_dir, tmp_path):
        script_file = tmp_path / "slow_script.R"
        script_file.write_text("# fake")
        mock_scripts_dir.__truediv__ = lambda self, name: script_file

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="Rscript", timeout=10)

        with pytest.raises(TimeoutError, match="超时"):
            run_r_script("slow_script.R", {}, timeout_seconds=10)


class TestRScriptError:
    def test_error_message_includes_script_name(self):
        err = RScriptError("test.R", "some error details", 1)
        assert "test.R" in str(err)
        assert "1" in str(err)

    def test_stderr_truncation(self):
        long_stderr = "x" * 1000
        err = RScriptError("test.R", long_stderr, 1)
        assert len(str(err)) < len(long_stderr) + 200

    def test_with_stdout_context(self):
        err = RScriptError("test.R", "err detail", 1, stdout="some output")
        msg = str(err)
        assert "stderr:" in msg
        assert "stdout:" in msg
