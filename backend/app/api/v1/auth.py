"""
认证 API — 双通道验证（Resend 邮件 + 阿里云短信）

端点：
  POST /auth/register             — 注册（邮箱 + 可选手机号）
  POST /auth/login                — 登录（未验证返回 403）
  GET  /auth/me                   — 当前用户信息
  POST /auth/refresh              — 刷新 Token
  POST /auth/change-password      — 修改密码
  POST /auth/consent              — 知情同意
  POST /auth/send-code            — 发送验证码（邮箱或短信）
  POST /auth/verify-code          — 验证验证码
  POST /auth/forgot-password      — 发送重置验证码
  POST /auth/reset-password       — 用验证码重置密码
  POST /auth/wechat-miniapp/login — 微信小程序登录（code2session）
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    ConsentRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    SendCodeRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserOut,
    VerifyCodeRequest,
)
from app.utils.auth import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


# ── 注册 ─────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已注册")

    if body.phone:
        phone_exists = await db.execute(select(User).where(User.phone == body.phone))
        if phone_exists.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="手机号已注册")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        phone=body.phone,
        email_verified=False,
    )
    db.add(user)
    await db.flush()

    db.add(AuditLog(
        user_id=user.id,
        action="USER_REGISTER",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    ))
    await db.commit()
    await db.refresh(user)

    # 同步发送验证码，失败时通知前端
    code_sent = True
    code_error = None
    try:
        from app.services.verification_service import send_verification_code
        await send_verification_code("email", user.email)
    except Exception as e:
        logger.error("注册后验证码发送失败: email=%s error=%s", user.email, e)
        code_sent = False
        code_error = str(e)

    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "code_sent": code_sent,
        "code_error": code_error,
    }


# ── 登录 ─────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="请先验证邮箱或手机号",
        )

    token = create_access_token({"sub": str(user.id)})

    db.add(AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


# ── 当前用户 / 刷新 / 改密码 / 知情同意 ─────────

@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: Annotated[User, Depends(get_current_user)]) -> TokenResponse:
    token = create_access_token({"sub": str(current_user.id)})
    return TokenResponse(access_token=token, expires_in=settings.jwt_access_expire_minutes * 60)


@router.post("/change-password", response_model=UserOut)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码错误")
    current_user.password_hash = hash_password(body.new_password)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/consent", response_model=UserOut)
async def give_consent(
    body: ConsentRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    current_user.consent_version = body.version
    current_user.consent_given_at = datetime.now(timezone.utc)
    db.add(AuditLog(
        user_id=current_user.id,
        action="CONSENT_GIVEN",
        metadata_={"version": body.version},
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()
    await db.refresh(current_user)
    return current_user


# ── 双通道验证码 ─────────────────────────────────

@router.post("/send-code")
async def send_code(body: SendCodeRequest) -> dict:
    """发送验证码到邮箱或手机（不需要登录）。"""
    if body.channel not in ("email", "sms"):
        raise HTTPException(status_code=400, detail="channel 必须为 email 或 sms")
    try:
        from app.services.verification_service import send_verification_code
        await send_verification_code(body.channel, body.target)
    except Exception as e:
        logger.error("验证码发送失败: channel=%s target=%s error=%s", body.channel, body.target, e)
        raise HTTPException(status_code=500, detail=f"验证码发送失败：{e}")
    return {"message": "验证码已发送，请查收"}


@router.post("/verify-code")
async def verify_code_endpoint(
    body: VerifyCodeRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """验证验证码并标记邮箱已验证。成功后自动返回 token，可直接登录。"""
    from app.services.verification_service import verify_code

    # 验证码尝试次数限制：同一 IP 每 10 分钟最多 5 次
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"verify_attempts:{client_ip}"
    attempts = await r.incr(rate_key)
    if attempts == 1:
        await r.expire(rate_key, 600)  # 10 分钟窗口
    if attempts > 5:
        await r.aclose()
        raise HTTPException(status_code=429, detail="验证尝试过于频繁，请 10 分钟后再试")
    await r.aclose()

    ok = await verify_code(f"verify:{body.channel}", body.target, body.code)
    if not ok:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 查找对应用户并标记验证
    if body.channel == "email":
        result = await db.execute(select(User).where(User.email == body.target))
    else:
        result = await db.execute(select(User).where(User.phone == body.target))

    user = result.scalar_one_or_none()
    if user and not user.email_verified:
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        await db.commit()

    # 验证成功后自动生成 token，前端可直接登录
    token = None
    if user:
        token = create_access_token({"sub": str(user.id)})

    return {
        "message": "验证成功",
        "verified": True,
        "access_token": token,
        "expires_in": settings.jwt_access_expire_minutes * 60 if token else None,
    }


# ── 忘记密码 / 重置密码 ──────────────────────────

@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """发送重置验证码（不泄露用户是否存在）。"""
    if body.channel == "email":
        result = await db.execute(select(User).where(User.email == body.target, User.is_active == True))
    elif body.channel == "sms":
        result = await db.execute(select(User).where(User.phone == body.target, User.is_active == True))
    else:
        raise HTTPException(status_code=400, detail="channel 必须为 email 或 sms")

    user = result.scalar_one_or_none()
    if user:
        try:
            from app.services.verification_service import send_reset_code
            await send_reset_code(body.channel, body.target)
        except Exception as e:
            # 记录错误但不泄露用户是否存在
            logger.error("重置验证码发送失败: channel=%s error=%s", body.channel, e)

    return {"message": "如果该账号已注册，验证码已发送"}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """用验证码重置密码。"""
    from app.services.verification_service import verify_code

    ok = await verify_code(f"reset:{body.channel}", body.target, body.code)
    if not ok:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    if body.channel == "email":
        result = await db.execute(select(User).where(User.email == body.target))
    else:
        result = await db.execute(select(User).where(User.phone == body.target))

    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password_hash = hash_password(body.new_password)
    await db.commit()

    return {"message": "密码重置成功，请使用新密码登录"}




# ── 微信小程序登录 ───────────────────────────────────────────────

class WechatMiniappLoginRequest(BaseModel):
    code: str  # wx.login() 返回的临时 code


@router.post("/wechat-miniapp/login", response_model=TokenResponse)
async def wechat_miniapp_login(
    body: WechatMiniappLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    微信小程序登录。

    流程：
      1. 小程序调用 wx.login() 拿到临时 code
      2. 将 code POST 到本接口
      3. 后端用 code 换取 openid（通过微信 jscode2session 接口）
      4. 查找或自动创建本地用户
      5. 返回 JWT token，后续请求与 Web 端完全一致
    """
    import httpx

    if not settings.wechat_miniapp_app_id or not settings.wechat_miniapp_app_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="微信小程序登录未配置，请联系管理员",
        )

    # 1. code → openid（调用腾讯官方接口，仅服务端可调用）
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": settings.wechat_miniapp_app_id,
                "secret": settings.wechat_miniapp_app_secret,
                "js_code": body.code,
                "grant_type": "authorization_code",
            },
        )

    wx_data = resp.json()
    if "errcode" in wx_data and wx_data["errcode"] != 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"微信登录失败：{wx_data.get('errmsg', '未知错误')}",
        )

    openid: str = wx_data["openid"]
    # unionid 在同一微信开放平台账号下跨小程序/公众号唯一（如已绑定则优先使用）
    unionid: str | None = wx_data.get("unionid")

    # 2. 查找已存在的小程序用户（以 wechat_miniapp + openid 为唯一键）
    result = await db.execute(
        select(User).where(
            User.oauth_provider == "wechat_miniapp",
            User.oauth_id == openid,
        )
    )
    user = result.scalar_one_or_none()

    # 如果有 unionid，尝试关联已有微信网页登录账号
    if user is None and unionid:
        result = await db.execute(
            select(User).where(User.oauth_id == unionid)
        )
        user = result.scalar_one_or_none()
        if user:
            # 补充小程序 openid 到现有账号
            user.wechat_openid = openid

    # 3. 首次登录 → 自动创建账号（小程序用户无邮箱，用占位地址）
    if user is None:
        user = User(
            email=f"wx_miniapp_{openid}@miniapp.local",
            password_hash=None,
            oauth_provider="wechat_miniapp",
            oauth_id=openid,
            wechat_openid=openid,
            wechat_unionid=unionid,
            email_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, token_type="bearer")
