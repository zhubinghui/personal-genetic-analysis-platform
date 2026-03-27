"""
基因数据文件格式校验

支持格式：
- Illumina IDAT（Red/Grn channel 二进制格式）
- Beta 值矩阵 CSV（探针 ID × 样本，值域 [0,1]）
"""

import io
import struct
from dataclasses import dataclass

import pandas as pd

# Illumina IDAT 文件魔数（前 4 字节）
IDAT_MAGIC = b"IDAT"

# IDAT header 中探针数量的偏移和格式（little-endian int32）
IDAT_PROBE_COUNT_OFFSET = 12

# 最小有效探针数（EPIC: ~850k，450K: ~450k，beta CSV 至少 10k）
MIN_PROBES_CSV = 10_000


@dataclass
class ValidationResult:
    valid: bool
    error: str | None = None
    probe_count: int | None = None


class FileValidator:
    def validate_idat(self, data: bytes, channel: str) -> ValidationResult:
        """
        校验 IDAT 文件。
        channel: 'Red' 或 'Grn'
        """
        if len(data) < 20:
            return ValidationResult(valid=False, error=f"[{channel}] 文件过小，不是有效 IDAT")

        if data[:4] != IDAT_MAGIC:
            return ValidationResult(
                valid=False,
                error=f"[{channel}] 魔数不匹配，不是 Illumina IDAT 格式（期望 'IDAT'，实际 {data[:4]!r}）",
            )

        # 读取探针数量（偏移 12，little-endian int32）
        try:
            probe_count = struct.unpack_from("<i", data, IDAT_PROBE_COUNT_OFFSET)[0]
        except struct.error:
            return ValidationResult(valid=False, error=f"[{channel}] 无法读取探针数量")

        if probe_count <= 0:
            return ValidationResult(valid=False, error=f"[{channel}] 探针数量无效: {probe_count}")

        return ValidationResult(valid=True, probe_count=probe_count)

    def validate_idat_pair(
        self, red_data: bytes, grn_data: bytes
    ) -> ValidationResult:
        """校验 Red/Grn IDAT 文件对，并确保探针数一致"""
        red_result = self.validate_idat(red_data, "Red")
        if not red_result.valid:
            return red_result

        grn_result = self.validate_idat(grn_data, "Grn")
        if not grn_result.valid:
            return grn_result

        if red_result.probe_count != grn_result.probe_count:
            return ValidationResult(
                valid=False,
                error=(
                    f"Red/Grn 探针数不匹配：Red={red_result.probe_count}, "
                    f"Grn={grn_result.probe_count}，请确认是同一样本的配对文件"
                ),
            )

        return ValidationResult(valid=True, probe_count=red_result.probe_count)

    def validate_beta_csv(self, data: bytes) -> ValidationResult:
        """
        校验 beta 值矩阵 CSV。
        要求：
        - 第一列为 CpG 探针 ID（以 'cg' 开头）
        - 值为 [0, 1] 区间的浮点数
        - 至少 MIN_PROBES_CSV 行探针
        """
        try:
            df = pd.read_csv(io.BytesIO(data), index_col=0, nrows=5)
        except Exception as e:
            return ValidationResult(valid=False, error=f"CSV 解析失败: {e}")

        if df.empty:
            return ValidationResult(valid=False, error="CSV 文件为空")

        first_probe = str(df.index[0])
        if not first_probe.startswith("cg"):
            return ValidationResult(
                valid=False,
                error=f"探针 ID 格式错误，应以 'cg' 开头，实际: {first_probe!r}",
            )

        # 检查第一列数值范围
        try:
            first_col = df.iloc[:, 0].astype(float)
            if (first_col < 0).any() or (first_col > 1).any():
                return ValidationResult(
                    valid=False, error="Beta 值超出 [0, 1] 范围"
                )
        except ValueError:
            return ValidationResult(valid=False, error="Beta 值列包含非数字内容")

        # 统计总行数
        try:
            total = sum(1 for _ in io.BytesIO(data)) - 1  # 减去 header
        except Exception:
            total = None

        if total is not None and total < MIN_PROBES_CSV:
            return ValidationResult(
                valid=False,
                error=f"探针数量不足（{total} < {MIN_PROBES_CSV}），请检查文件完整性",
            )

        return ValidationResult(valid=True, probe_count=total)
