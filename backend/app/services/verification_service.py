"""
验证码管理服务 — Redis 存储

统一管理邮箱和短信验证码的生成、存储和校验。
验证码为 6 位数字，存储在 Redis 中，带 TTL 自动过期。
"""

import logging
import secrets

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _key(purpose: str, target: str) -> str:
    """生成 Redis key，如 verify:email:user@example.com"""
    return f"{purpose}:{target}"


def generate_code() -> str:
    """生成 6 位数字验证码。"""
    return f"{secrets.randbelow(1_000_000):06d}"


async def store_code(purpose: str, target: str, code: str) -> None:
    """存储验证码到 Redis，自动过期。"""
    r = await _get_redis()
    key = _key(purpose, target)
    ttl = settings.verify_code_expire_minutes * 60
    await r.setex(key, ttl, code)
    logger.info("验证码已存储: purpose=%s target=%s ttl=%ds", purpose, target, ttl)


async def verify_code(purpose: str, target: str, code: str) -> bool:
    """校验验证码，成功后自动删除（一次性使用）。"""
    r = await _get_redis()
    key = _key(purpose, target)
    stored = await r.get(key)

    if stored is None:
        return False
    if stored != code:
        return False

    await r.delete(key)  # 验证成功，删除（防重放）
    return True


async def send_verification_code(channel: str, target: str) -> str:
    """
    生成并发送验证码。

    channel: "email" 或 "sms"
    target:  邮箱地址或手机号
    返回：生成的验证码（供日志/测试用）
    """
    code = generate_code()
    await store_code(f"verify:{channel}", target, code)

    if channel == "email":
        from app.services.email_service import send_verification_email
        await send_verification_email(target, code)
    elif channel == "sms":
        from app.services.sms_service import send_verification_sms
        await send_verification_sms(target, code)

    return code


async def send_reset_code(channel: str, target: str) -> str:
    """生成并发送密码重置验证码。"""
    code = generate_code()
    await store_code(f"reset:{channel}", target, code)

    if channel == "email":
        from app.services.email_service import send_reset_email
        await send_reset_email(target, code)
    elif channel == "sms":
        from app.services.sms_service import send_reset_sms
        await send_reset_sms(target, code)

    return code
