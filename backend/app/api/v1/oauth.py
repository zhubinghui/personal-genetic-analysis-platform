"""
OAuth2 第三方登录 API

端点：
  GET  /auth/oauth/providers             — 返回已配置的登录方式列表
  GET  /auth/oauth/{provider}/authorize  — 生成授权 URL
  GET  /auth/oauth/{provider}/callback   — 处理授权回调 → 签发 JWT → 重定向前端
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.oauth_providers import PROVIDERS, generate_state, get_provider
from app.utils.auth import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oauth", tags=["OAuth 第三方登录"])


@router.get("/providers")
async def list_providers() -> dict:
    """返回已配置的 OAuth 登录方式。"""
    available = []
    for name, provider in PROVIDERS.items():
        available.append({
            "name": name,
            "configured": provider.is_configured(),
            "label": {"github": "GitHub", "google": "Google", "wechat": "微信"}.get(name, name),
        })
    return {"providers": available}


@router.get("/{provider}/authorize")
async def authorize(provider: str) -> dict:
    """生成第三方授权 URL，前端跳转到此 URL。"""
    p = get_provider(provider)
    if not p.is_configured():
        raise HTTPException(status_code=400, detail=f"{provider} 登录未配置")

    state = generate_state()
    url = p.get_authorize_url(state)

    # state 存 Redis 做 CSRF 校验（简化方案：暂不校验，后续加 Redis）
    return {"authorize_url": url, "state": state}


@router.get("/{provider}/callback")
async def callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    处理第三方平台授权回调。
    1. 用 code 换 access_token
    2. 获取用户信息
    3. 查找或创建本地用户
    4. 签发 JWT → 重定向到前端 /auth/callback?token=xxx
    """
    p = get_provider(provider)
    if not p.is_configured():
        raise HTTPException(status_code=400, detail=f"{provider} 登录未配置")

    try:
        # 换取 token + 用户信息
        access_token = await p.exchange_token(code)
        user_info = await p.get_user_info(access_token)
    except Exception as e:
        logger.error("OAuth %s 认证失败: %s", provider, e)
        return RedirectResponse(f"{settings.frontend_url}/login?error=oauth_failed")

    # 查找已存在的 OAuth 用户
    result = await db.execute(
        select(User).where(
            User.oauth_provider == user_info.provider,
            User.oauth_id == user_info.oauth_id,
        )
    )
    user = result.scalar_one_or_none()

    if user is None and user_info.email:
        # 尝试通过邮箱关联现有账号
        result = await db.execute(select(User).where(User.email == user_info.email))
        user = result.scalar_one_or_none()
        if user:
            # 关联 OAuth 信息到现有账号
            user.oauth_provider = user_info.provider
            user.oauth_id = user_info.oauth_id
            if user_info.avatar_url and not user.avatar_url:
                user.avatar_url = user_info.avatar_url

    if user is None:
        # 自动创建新用户
        if not user_info.email:
            # 微信等平台可能无邮箱，生成占位邮箱
            user_info.email = f"{user_info.provider}_{user_info.oauth_id}@oauth.local"

        user = User(
            email=user_info.email,
            password_hash=None,  # OAuth 用户无密码
            oauth_provider=user_info.provider,
            oauth_id=user_info.oauth_id,
            avatar_url=user_info.avatar_url,
            email_verified=True,  # 信任第三方平台的邮箱验证
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)

    # 更新头像
    if user_info.avatar_url:
        user.avatar_url = user_info.avatar_url

    # 确保 OAuth 用户标记已验证
    if not user.email_verified:
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    # 签发 JWT
    jwt_token = create_access_token({"sub": str(user.id)})

    # 重定向到前端回调页
    return RedirectResponse(f"{settings.frontend_url}/auth/callback?token={jwt_token}")
