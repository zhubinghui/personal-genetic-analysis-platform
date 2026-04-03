"""Shared fixtures for analysis engine tests."""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def qc_passed_raw() -> dict:
    return json.loads((FIXTURES_DIR / "mock_qc_passed.json").read_text())


@pytest.fixture
def qc_failed_raw() -> dict:
    return json.loads((FIXTURES_DIR / "mock_qc_failed.json").read_text())


@pytest.fixture
def horvath_raw() -> dict:
    return json.loads((FIXTURES_DIR / "mock_horvath.json").read_text())


@pytest.fixture
def grimage_raw() -> dict:
    return json.loads((FIXTURES_DIR / "mock_grimage.json").read_text())


@pytest.fixture
def phenoage_raw() -> dict:
    return json.loads((FIXTURES_DIR / "mock_phenoage.json").read_text())


@pytest.fixture
def dunedinpace_raw() -> dict:
    return json.loads((FIXTURES_DIR / "mock_dunedinpace.json").read_text())
