"""
Worker 容器侧的存储服务适配器（独立于 FastAPI backend）
"""

import base64
import hashlib
import io
import os
import uuid
import asyncio
from typing import Optional

from minio import Minio


def _decrypt_file(data: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = data[:12]
    ciphertext = data[12:]
    return AESGCM(key).decrypt(nonce, ciphertext, None)


class WorkerStorageService:
    def __init__(self) -> None:
        self.client = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=os.getenv("MINIO_ROOT_PASSWORD", "changeme"),
            secure=os.getenv("MINIO_USE_SSL", "false").lower() == "true",
        )
        enc_key_b64 = os.getenv("FILE_ENCRYPTION_KEY", "")
        self._enc_key = base64.b64decode(enc_key_b64) if enc_key_b64 else b"\x00" * 32

    async def download_decrypted(self, object_key: str, bucket: str) -> bytes:
        response = await asyncio.to_thread(self.client.get_object, bucket, object_key)
        encrypted = response.read()
        response.close()
        response.release_conn()
        return _decrypt_file(encrypted, self._enc_key)


_instance: Optional[WorkerStorageService] = None


def get_storage_service() -> WorkerStorageService:
    global _instance
    if _instance is None:
        _instance = WorkerStorageService()
    return _instance
