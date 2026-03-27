"""
AES-256-GCM 文件加密工具

存储格式: nonce(12B) || ciphertext || GCM_tag(16B)
GCM tag 由 cryptography 库自动附加到 ciphertext 末尾。
解密时若 tag 不匹配，抛出 InvalidTag，即数据被篡改。
"""

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_file(plaintext: bytes, key: bytes) -> bytes:
    """加密文件内容，返回 nonce + ciphertext(含GCM tag)"""
    if len(key) != 32:
        raise ValueError("密钥必须为 32 字节（AES-256）")
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_file(data: bytes, key: bytes) -> bytes:
    """解密文件内容，若数据被篡改则抛出 InvalidTag"""
    if len(data) < 12 + 16:
        raise ValueError("数据太短，不是有效的加密文件")
    nonce = data[:12]
    ciphertext = data[12:]
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag as e:
        raise ValueError("文件完整性验证失败，数据可能被篡改") from e
