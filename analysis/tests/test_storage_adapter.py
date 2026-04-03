"""Tests for analysis/pipeline/storage_adapter.py — encryption round-trip."""

import base64
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.storage_adapter import _decrypt_file


class TestDecryptFile:
    def _encrypt(self, data: bytes, key: bytes) -> bytes:
        """Helper: encrypt data using the same scheme as the backend."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = os.urandom(12)
        ciphertext = AESGCM(key).encrypt(nonce, data, None)
        return nonce + ciphertext

    def test_roundtrip(self):
        key = os.urandom(32)
        plaintext = b"test genetic data content"
        encrypted = self._encrypt(plaintext, key)
        result = _decrypt_file(encrypted, key)
        assert result == plaintext

    def test_large_data_roundtrip(self):
        key = os.urandom(32)
        plaintext = os.urandom(1024 * 1024)  # 1 MB
        encrypted = self._encrypt(plaintext, key)
        result = _decrypt_file(encrypted, key)
        assert result == plaintext

    def test_wrong_key_raises(self):
        key = os.urandom(32)
        wrong_key = os.urandom(32)
        encrypted = self._encrypt(b"secret", key)

        from cryptography.exceptions import InvalidTag
        with pytest.raises(InvalidTag):
            _decrypt_file(encrypted, wrong_key)

    def test_corrupted_ciphertext_raises(self):
        key = os.urandom(32)
        encrypted = self._encrypt(b"data", key)
        corrupted = encrypted[:15] + bytes([encrypted[15] ^ 0xFF]) + encrypted[16:]

        from cryptography.exceptions import InvalidTag
        with pytest.raises(InvalidTag):
            _decrypt_file(corrupted, key)

    def test_empty_plaintext(self):
        key = os.urandom(32)
        plaintext = b""
        encrypted = self._encrypt(plaintext, key)
        result = _decrypt_file(encrypted, key)
        assert result == b""
