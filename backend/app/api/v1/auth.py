"""
认证 API

端点：
  POST /auth/register           — 注册（发送验证邮件）
  POST /auth/login              — 登录（未验证返回 403）
  GET  /auth/me                 — 当前用户信息
  POST /auth/refresh            — 刷新 Token
  POST /auth/change-password    — 修改密码
  POST /auth/consent            — 知情同意
  GET  /auth/verify-email       — 邮箱验证
  POST /auth/resend-verification — 重发验证邮件
  POST /auth/forgot-password    — 发送重置邮件
  POST /auth/reset-password     — 重置密码
"""

import asyncio
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
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
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.utils.auth import (
    create_access_token,
    create_reset_token,
    create_verification_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["认证"])


# ── 注册 ─────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已注册")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
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

    # 后台发送验证邮件
    background_tasks.add_task(_send_verification, user.email, str(user.id))

    return user


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
            detail="请先验证邮箱，查看您的收件箱或点击重新发送验证邮件",
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


# ── 当前用户 ─────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


# ── Token 刷新 ───────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: Annotated[User, Depends(get_current_user)],
) -> TokenResponse:
    token = create_access_token({"sub": str(current_user.id)})
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


# ── 修改密码 ─────────────────────────────────────

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


# ── 知情同意 ─────────────────────────────────────

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


# ── 邮箱验证 ─────────────────────────────────────

@router.get("/verify-email")
async def verify_email(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    payload = decode_token(token, "verify")
    if payload is None:
        raise HTTPException(status_code=400, detail="验证链接无效或已过期，请重新发送")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.email_verified:
        return {"message": "邮箱已验证，无需重复操作", "verified": True}

    user.email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "邮箱验证成功！现在可以登录了", "verified": True}


@router.post("/resend-verification")
async def resend_verification(
    body: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """重新发送验证邮件（不泄露用户是否存在）。"""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user and not user.email_verified:
        background_tasks.add_task(_send_verification, user.email, str(user.id))

    # 无论用户是否存在都返回相同响应（安全设计）
    return {"message": "如果该邮箱已注册且未验证，验证邮件已发送到您的邮箱"}


# ── 忘记密码 ─────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """发送密码重置邮件（不泄露用户是否存在）。"""
    result = await db.execute(select(User).where(User.email == body.email, User.is_active == True))
    user = result.scalar_one_or_none()

    if user:
        token = create_reset_token(str(user.id))
        background_tasks.add_task(_send_reset, user.email, token)

    # 无论用户是否存在都返回相同响应（安全设计）
    return {"message": "如果该邮箱已注册，密码重置邮件已发送"}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    payload = decode_token(body.token, "reset")
    if payload is None:
        raise HTTPException(status_code=400, detail="重置链接无效或已过期，请重新申请")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password_hash = hash_password(body.new_password)
    await db.commit()

    return {"message": "密码重置成功，请使用新密码登录"}


# ── 内部辅助函数 ──────────────────────────────────

async def _send_verification(email: str, user_id: str) -> None:
    try:
        from app.services.email_service import send_verification_email
        token = create_verification_token(user_id)
        await send_verification_email(email, token)
    except Exception:
        pass  # 邮件发送失败不阻断注册流程


async def _send_reset(email: str, token: str) -> None:
    try:
        from app.services.email_service import send_reset_email
        await send_reset_email(email, token)
    except Exception:
        pass  # 邮件发送失败不阻断流程
