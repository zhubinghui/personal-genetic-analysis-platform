from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ── Access Token ─────────────────────────────────

def create_access_token(data: dict[str, Any]) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload.update({"exp": expire, "type": "access"})
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


# ── Email Verification Token ─────────────────────

def create_verification_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.email_verify_expire_hours)
    payload = {"sub": user_id, "exp": expire, "type": "verify"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# ── Password Reset Token ─────────────────────────

def create_reset_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_expire_minutes)
    payload = {"sub": user_id, "exp": expire, "type": "reset"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# ── 通用 Token 解码 ──────────────────────────────

def decode_token(token: str, expected_type: str) -> dict | None:
    """解码并验证指定类型的 JWT Token。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None
