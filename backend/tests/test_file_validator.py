"""文件格式校验单元测试（IDAT / Beta CSV）"""

import struct

import pytest

from app.services.file_validator import IDAT_MAGIC, FileValidator, ValidationResult

validator = FileValidator()


def _make_idat(probe_count: int = 850_000) -> bytes:
    """构造最小有效 IDAT 二进制数据。"""
    header = IDAT_MAGIC + b"\x01\x00\x00\x00"  # magic + version
    header += b"\x00\x00\x00\x00"               # padding to offset 12
    header += struct.pack("<i", probe_count)     # probe count at offset 12
    header += b"\x00" * 100                      # 填充至足够长
    return header


class TestIdatValidation:
    def test_valid_idat(self):
        data = _make_idat(850_000)
        result = validator.validate_idat(data, "Red")
        assert result.valid is True
        assert result.probe_count == 850_000

    def test_too_small(self):
        result = validator.validate_idat(b"\x00" * 10, "Red")
        assert result.valid is False
        assert "过小" in result.error

    def test_wrong_magic(self):
        data = b"XXXX" + b"\x00" * 100
        result = validator.validate_idat(data, "Grn")
        assert result.valid is False
        assert "魔数" in result.error

    def test_zero_probe_count(self):
        data = _make_idat(0)
        result = validator.validate_idat(data, "Red")
        assert result.valid is False
        assert "无效" in result.error

    def test_negative_probe_count(self):
        data = _make_idat(-1)
        result = validator.validate_idat(data, "Red")
        assert result.valid is False


class TestIdatPairValidation:
    def test_matching_pair(self):
        red = _make_idat(850_000)
        grn = _make_idat(850_000)
        result = validator.validate_idat_pair(red, grn)
        assert result.valid is True
        assert result.probe_count == 850_000

    def test_mismatched_probe_counts(self):
        red = _make_idat(850_000)
        grn = _make_idat(450_000)
        result = validator.validate_idat_pair(red, grn)
        assert result.valid is False
        assert "不匹配" in result.error

    def test_invalid_red_propagates(self):
        red = b"INVALID"
        grn = _make_idat(850_000)
        result = validator.validate_idat_pair(red, grn)
        assert result.valid is False


class TestBetaCsvValidation:
    def _make_csv(self, probes: int = 15_000, value: float = 0.5) -> bytes:
        rows = ["probe_id,sample1"]
        for i in range(probes):
            rows.append(f"cg{i:08d},{value}")
        return "\n".join(rows).encode()

    def test_valid_csv(self):
        result = validator.validate_beta_csv(self._make_csv())
        assert result.valid is True

    def test_too_few_probes(self):
        result = validator.validate_beta_csv(self._make_csv(probes=100))
        assert result.valid is False
        assert "不足" in result.error

    def test_wrong_probe_prefix(self):
        data = b"probe_id,sample1\nXYZ001,0.5\nXYZ002,0.3"
        result = validator.validate_beta_csv(data)
        assert result.valid is False
        assert "cg" in result.error

    def test_value_out_of_range(self):
        result = validator.validate_beta_csv(self._make_csv(probes=15_000, value=1.5))
        assert result.valid is False
        assert "范围" in result.error

    def test_empty_csv(self):
        result = validator.validate_beta_csv(b"")
        assert result.valid is False

    def test_non_numeric_values(self):
        data = b"probe_id,sample1\ncg00000001,abc\ncg00000002,def"
        result = validator.validate_beta_csv(data)
        assert result.valid is False
