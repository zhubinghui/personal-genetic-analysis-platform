from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.user import ConsentRequest, TokenResponse, UserCreate, UserLogin, UserOut
from app.utils.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已注册")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
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
    return user


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

    token = create_access_token({"sub": str(user.id)})

    db.add(AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    ))
    await db.commit()

    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
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
