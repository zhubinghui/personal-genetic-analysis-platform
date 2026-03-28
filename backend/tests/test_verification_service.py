"""验证码服务单元测试"""

import pytest

from app.services.verification_service import _key, generate_code


class TestGenerateCode:
    def test_returns_6_digits(self):
        code = generate_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_padded_with_zeros(self):
        """确保小数字也是 6 位（前补零）。"""
        codes = [generate_code() for _ in range(100)]
        assert all(len(c) == 6 for c in codes)

    def test_unique_across_calls(self):
        codes = {generate_code() for _ in range(50)}
        # 50 次中应有绝大部分不重复（概率极高）
        assert len(codes) > 30


class TestKeyFormat:
    def test_email_key(self):
        key = _key("verify:email", "user@example.com")
        assert key == "verify:email:user@example.com"

    def test_sms_key(self):
        key = _key("reset:sms", "13800138000")
        assert key == "reset:sms:13800138000"

    def test_format_consistency(self):
        key = _key("purpose", "target")
        assert key == "purpose:target"
