"""AES-256-GCM 加密/解密单元测试"""

import os

import pytest

from app.utils.encryption import decrypt_file, encrypt_file


@pytest.fixture
def key() -> bytes:
    return os.urandom(32)


class TestEncryptDecrypt:
    def test_roundtrip(self, key: bytes):
        """加密后解密应返回原始明文。"""
        plaintext = b"Hello, epigenetic world!"
        encrypted = encrypt_file(plaintext, key)
        assert decrypt_file(encrypted, key) == plaintext

    def test_roundtrip_empty(self, key: bytes):
        """空数据加密/解密往返。"""
        encrypted = encrypt_file(b"", key)
        assert decrypt_file(encrypted, key) == b""

    def test_roundtrip_large(self, key: bytes):
        """大文件（1MB）加密/解密往返。"""
        plaintext = os.urandom(1024 * 1024)
        encrypted = encrypt_file(plaintext, key)
        assert decrypt_file(encrypted, key) == plaintext

    def test_ciphertext_differs(self, key: bytes):
        """同一明文两次加密结果不同（随机 nonce）。"""
        plaintext = b"deterministic?"
        c1 = encrypt_file(plaintext, key)
        c2 = encrypt_file(plaintext, key)
        assert c1 != c2  # nonce 不同

    def test_output_format(self, key: bytes):
        """密文格式：nonce(12B) + ciphertext + GCM_tag(16B)。"""
        plaintext = b"test"
        encrypted = encrypt_file(plaintext, key)
        assert len(encrypted) >= 12 + 16 + len(plaintext)

    def test_tamper_detection(self, key: bytes):
        """篡改密文应抛出 ValueError。"""
        encrypted = encrypt_file(b"sensitive data", key)
        tampered = bytearray(encrypted)
        tampered[-1] ^= 0xFF  # 翻转最后一个字节
        with pytest.raises(ValueError, match="篡改"):
            decrypt_file(bytes(tampered), key)

    def test_wrong_key_rejected(self):
        """错误密钥解密应失败。"""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        encrypted = encrypt_file(b"secret", key1)
        with pytest.raises(ValueError):
            decrypt_file(encrypted, key2)

    def test_short_key_rejected(self):
        """非 32 字节密钥应抛出 ValueError。"""
        with pytest.raises(ValueError, match="32 字节"):
            encrypt_file(b"data", b"short")

    def test_short_data_rejected(self, key: bytes):
        """过短数据（< 28B）解密应失败。"""
        with pytest.raises(ValueError, match="太短"):
            decrypt_file(b"too short", key)
