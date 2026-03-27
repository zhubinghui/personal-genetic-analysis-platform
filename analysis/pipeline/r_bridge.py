"""
R-Python 通信桥接层

策略：subprocess + JSON 文件通信（非 rpy2）
- R 脚本从 --input 临时 JSON 文件读取输入
- R 脚本将结果以 JSON 写入 stdout
- Python 解析 stdout，转换为 dict

优势：R 崩溃只影响子进程；JSON 通信透明可调试
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import structlog

logger = structlog.get_logger()

RSCRIPT = os.getenv("RSCRIPT_PATH", "/usr/local/bin/Rscript")
SCRIPTS_DIR = Path(__file__).parent.parent / "r_scripts"


class RScriptError(Exception):
    def __init__(self, script: str, stderr: str, returncode: int, stdout: str = "") -> None:
        self.script = script
        self.stderr = stderr
        self.returncode = returncode
        detail = f"stderr: {stderr[-400:]}\nstdout: {stdout[:200]}" if stdout.strip() else stderr[-500:]
        super().__init__(f"R 脚本 {script} 返回错误码 {returncode}:\n{detail}")


def run_r_script(
    script_name: str,
    input_args: dict,
    timeout_seconds: int = 3600,
) -> dict:
    """
    执行 R 脚本，返回解析后的 JSON 结果。

    Args:
        script_name:     R 脚本文件名（相对于 r_scripts/ 目录）
        input_args:      传递给 R 脚本的输入参数（将序列化为 JSON 文件）
        timeout_seconds: 超时秒数，默认 1 小时

    Returns:
        R 脚本输出的 JSON 解析结果

    Raises:
        RScriptError: R 脚本返回非零状态码
        ValueError:   R 脚本输出无法解析为 JSON
        TimeoutError: 超时
    """
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"R 脚本不存在: {script_path}")

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8"
    ) as f:
        json.dump(input_args, f)
        input_file = f.name

    try:
        logger.info("执行 R 脚本", script=script_name, input_keys=list(input_args.keys()))

        result = subprocess.run(
            [RSCRIPT, "--vanilla", str(script_path), "--input", input_file],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

        # 记录 R 的 stderr（包含 message() 输出）
        if result.stderr:
            logger.debug("R 脚本 stderr", script=script_name, stderr=result.stderr[-1000:])

        if result.returncode != 0:
            raise RScriptError(script_name, result.stderr, result.returncode, result.stdout)

        if not result.stdout.strip():
            raise ValueError(f"R 脚本 {script_name} 没有输出任何内容")

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"R 脚本 {script_name} 输出无法解析为 JSON: {e}\n输出: {result.stdout[:200]}"
            ) from e

    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"R 脚本 {script_name} 超时（{timeout_seconds}s）") from e
    finally:
        os.unlink(input_file)
