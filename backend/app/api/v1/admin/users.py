"""
管理员用户管理 API

端点：
  GET    /admin/users              — 列出所有用户
  PATCH  /admin/users/{id}/role    — 设置/取消管理员角色
  PATCH  /admin/users/{id}/status  — 启用/禁用用户
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_admin_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    AdminSetRoleRequest,
    AdminSetStatusRequest,
    AdminUserListResponse,
    AdminUserOut,
)

router = APIRouter(prefix="/admin/users", tags=["管理员-用户管理"])


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    _: Annotated[User, Depends(get_admin_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    items = (
        await db.execute(
            select(User).order_by(User.created_at.desc()).offset(skip).limit(min(limit, 100))
        )
    ).scalars().all()
    return AdminUserListResponse(total=total, items=items)


@router.patch("/{user_id}/role", response_model=AdminUserOut)
async def set_user_role(
    user_id: uuid.UUID,
    body: AdminSetRoleRequest,
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的管理员角色")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_admin = body.is_admin
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=AdminUserOut)
async def set_user_status(
    user_id: uuid.UUID,
    body: AdminSetStatusRequest,
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能禁用自己的账号")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_active = body.is_active
    await db.commit()
    await db.refresh(user)
    return user
