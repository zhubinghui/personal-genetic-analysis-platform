"""
MinIO 对象存储服务，所有文件经 AES-256-GCM 加密后存储。

对象键格式：{pseudonym_id}/{sample_id}/{filename}.enc
前缀使用 pseudonym_id（而非 user_id）强化隐私隔离。
"""

import asyncio
import hashlib
import io
import uuid

from minio import Minio
from minio.error import S3Error

from app.config import settings
from app.utils.encryption import decrypt_file, encrypt_file


class StorageService:
    def __init__(self) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_use_ssl,
        )

    async def upload_encrypted(
        self,
        pseudonym_id: uuid.UUID,
        sample_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        bucket: str,
    ) -> tuple[str, str]:
        """
        加密并上传文件到 MinIO。
        返回 (object_key, sha256_of_plaintext)
        sha256 在加密前计算，用于后续完整性验证。
        """
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        encrypted = encrypt_file(file_bytes, settings.file_encryption_key_bytes)

        object_key = f"{pseudonym_id}/{sample_id}/{filename}.enc"

        await asyncio.to_thread(
            self.client.put_object,
            bucket,
            object_key,
            io.BytesIO(encrypted),
            len(encrypted),
            content_type="application/octet-stream",
        )

        return object_key, file_hash

    async def download_decrypted(self, object_key: str, bucket: str) -> bytes:
        """从 MinIO 下载并解密文件"""
        response = await asyncio.to_thread(self.client.get_object, bucket, object_key)
        encrypted = response.read()
        response.close()
        response.release_conn()
        return decrypt_file(encrypted, settings.file_encryption_key_bytes)

    async def delete_object(self, object_key: str, bucket: str) -> None:
        """删除 MinIO 对象（GDPR 删除权）"""
        try:
            await asyncio.to_thread(self.client.remove_object, bucket, object_key)
        except S3Error:
            pass  # 对象不存在时忽略

    async def verify_integrity(
        self, object_key: str, bucket: str, expected_hash: str
    ) -> bool:
        """下载解密后验证 SHA-256 完整性"""
        plaintext = await self.download_decrypted(object_key, bucket)
        actual_hash = hashlib.sha256(plaintext).hexdigest()
        return actual_hash == expected_hash


_storage_service: StorageService | None = None


def get_storage() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
