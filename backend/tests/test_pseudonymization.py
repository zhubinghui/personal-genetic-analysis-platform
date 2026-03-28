"""伪名化工具单元测试"""

import uuid
from unittest.mock import MagicMock

from app.utils.pseudonymization import get_pseudonym_id, make_object_key


class TestGetPseudonymId:
    def test_returns_pseudonym_not_user_id(self):
        """应返回 pseudonym_id 而非 user.id。"""
        user = MagicMock()
        user.id = uuid.uuid4()
        user.pseudonym_id = uuid.uuid4()
        assert user.id != user.pseudonym_id  # 二者不同

        result = get_pseudonym_id(user)
        assert result == user.pseudonym_id
        assert result != user.id


class TestMakeObjectKey:
    def test_key_format(self):
        pseudo = uuid.UUID("11111111-1111-1111-1111-111111111111")
        sample = uuid.UUID("22222222-2222-2222-2222-222222222222")
        key = make_object_key(pseudo, sample, "report.pdf")
        assert key == "11111111-1111-1111-1111-111111111111/22222222-2222-2222-2222-222222222222/report.pdf.enc"

    def test_key_uses_pseudonym_not_user_id(self):
        """对象键路径中不应出现 user.id。"""
        user_id = uuid.uuid4()
        pseudo = uuid.uuid4()
        sample = uuid.uuid4()
        key = make_object_key(pseudo, sample, "data.idat")
        assert str(pseudo) in key
        assert str(user_id) not in key

    def test_enc_suffix(self):
        key = make_object_key(uuid.uuid4(), uuid.uuid4(), "myfile.txt")
        assert key.endswith(".enc")
