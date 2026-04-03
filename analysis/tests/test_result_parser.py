"""Tests for analysis/pipeline/result_parser.py"""

import sys
from pathlib import Path

# Ensure pipeline package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.result_parser import (
    QCResult,
    ClockResults,
    AnalysisPipelineResult,
    parse_qc_result,
    parse_clock_results,
    compute_acceleration,
    _to_float,
)


# ── _to_float edge cases ────────────────────────────────────────

class TestToFloat:
    def test_normal_int(self):
        assert _to_float(42) == 42.0

    def test_normal_float(self):
        assert _to_float(3.14) == 3.14

    def test_string_number(self):
        assert _to_float("43.7") == 43.7

    def test_none_returns_none(self):
        assert _to_float(None) is None

    def test_nan_returns_none(self):
        assert _to_float(float("nan")) is None

    def test_inf_returns_none(self):
        assert _to_float(float("inf")) is None

    def test_neg_inf_returns_none(self):
        assert _to_float(float("-inf")) is None

    def test_empty_string_returns_none(self):
        assert _to_float("") is None

    def test_na_string_returns_none(self):
        assert _to_float("NA") is None

    def test_non_numeric_string_returns_none(self):
        assert _to_float("not_a_number") is None

    def test_bool_true(self):
        assert _to_float(True) == 1.0

    def test_zero(self):
        assert _to_float(0) == 0.0

    def test_negative(self):
        assert _to_float(-5.3) == -5.3


class TestParseQCResult:
    def test_qc_passed(self, qc_passed_raw):
        result = parse_qc_result(qc_passed_raw)
        assert isinstance(result, QCResult)
        assert result.qc_passed is True
        assert result.error is None
        assert result.n_probes_before == 866091
        assert result.n_probes_after == 785302
        assert result.detection_p_failed_fraction == 0.002
        assert result.beta_matrix_path is not None

    def test_qc_failed(self, qc_failed_raw):
        result = parse_qc_result(qc_failed_raw)
        assert result.qc_passed is False
        assert result.error is not None
        assert "12.3%" in result.error
        assert result.beta_matrix_path is None

    def test_empty_dict_defaults_to_failed(self):
        result = parse_qc_result({})
        assert result.qc_passed is False
        assert result.error is None

    def test_minimal_pass(self):
        result = parse_qc_result({"qc_passed": True})
        assert result.qc_passed is True
        assert result.n_probes_before is None


class TestParseClockResults:
    def test_all_clocks_present(self, horvath_raw, grimage_raw, phenoage_raw, dunedinpace_raw):
        result = parse_clock_results(horvath_raw, grimage_raw, phenoage_raw, dunedinpace_raw)
        assert isinstance(result, ClockResults)
        assert result.horvath_age == 43.7
        assert result.grimage_age == 46.2
        assert result.phenoage_age == 41.5
        assert result.dunedinpace == 1.032
        assert result.dunedinpace_dimensions is not None
        assert result.dunedinpace_dimensions["cardiovascular"] == 1.05
        assert len(result.dunedinpace_dimensions) == 9

    def test_missing_keys_return_none(self):
        result = parse_clock_results({}, {}, {}, {})
        assert result.horvath_age is None
        assert result.grimage_age is None
        assert result.phenoage_age is None
        assert result.dunedinpace is None
        assert result.dunedinpace_dimensions is None

    def test_nan_values_converted_to_none(self):
        result = parse_clock_results(
            {"horvath_age": float("nan")},
            {"grimage_age": float("inf")},
            {"phenoage_age": 41.5},
            {"dunedinpace": None},
        )
        assert result.horvath_age is None
        assert result.grimage_age is None
        assert result.phenoage_age == 41.5
        assert result.dunedinpace is None


class TestComputeAcceleration:
    def test_positive_acceleration(self):
        result = compute_acceleration(45.0, 40)
        assert result == 5.0

    def test_negative_acceleration(self):
        result = compute_acceleration(38.0, 40)
        assert result == -2.0

    def test_none_horvath(self):
        assert compute_acceleration(None, 40) is None

    def test_none_chronological(self):
        assert compute_acceleration(45.0, None) is None

    def test_both_none(self):
        assert compute_acceleration(None, None) is None

    def test_rounding(self):
        result = compute_acceleration(43.777, 40)
        assert result == 3.78


class TestAnalysisPipelineResult:
    def test_default_clocks(self):
        qc = QCResult(qc_passed=False, error="test")
        result = AnalysisPipelineResult(qc=qc)
        assert result.clocks.horvath_age is None
        assert result.biological_age_acceleration is None
