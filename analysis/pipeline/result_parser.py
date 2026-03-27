"""
解析各 R 脚本的输出结果并组合为最终分析结果。
"""

from dataclasses import dataclass, field


@dataclass
class QCResult:
    qc_passed: bool
    error: str | None = None
    n_probes_before: int | None = None
    n_probes_after: int | None = None
    detection_p_failed_fraction: float | None = None
    beta_matrix_path: str | None = None


@dataclass
class ClockResults:
    horvath_age: float | None = None
    grimage_age: float | None = None
    phenoage_age: float | None = None
    dunedinpace: float | None = None
    dunedinpace_dimensions: dict | None = None


@dataclass
class AnalysisPipelineResult:
    qc: QCResult
    clocks: ClockResults = field(default_factory=ClockResults)
    biological_age_acceleration: float | None = None


def parse_qc_result(raw: dict) -> QCResult:
    return QCResult(
        qc_passed=bool(raw.get("qc_passed", False)),
        error=raw.get("error"),
        n_probes_before=raw.get("n_probes_before"),
        n_probes_after=raw.get("n_probes_after"),
        detection_p_failed_fraction=raw.get("detection_p_failed_fraction"),
        beta_matrix_path=raw.get("beta_matrix_path"),
    )


def _to_float(val) -> float | None:
    """将 R JSON 输出的值转为 float，处理 null/NaN/Inf 字符串。"""
    if val is None:
        return None
    try:
        f = float(val)
        return f if (f == f and abs(f) != float("inf")) else None  # NaN/Inf → None
    except (TypeError, ValueError):
        return None


def parse_clock_results(
    horvath_raw: dict,
    grimage_raw: dict,
    phenoage_raw: dict,
    dunedinpace_raw: dict,
) -> ClockResults:
    return ClockResults(
        horvath_age=_to_float(horvath_raw.get("horvath_age")),
        grimage_age=_to_float(grimage_raw.get("grimage_age")),
        phenoage_age=_to_float(phenoage_raw.get("phenoage_age")),
        dunedinpace=_to_float(dunedinpace_raw.get("dunedinpace")),
        dunedinpace_dimensions=dunedinpace_raw.get("dimensions"),
    )


def compute_acceleration(
    horvath_age: float | None,
    chronological_age: int | None,
) -> float | None:
    if horvath_age is None or chronological_age is None:
        return None
    return round(horvath_age - chronological_age, 2)
