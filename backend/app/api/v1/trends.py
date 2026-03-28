"""
纵向对比 API

GET /trends — 返回当前用户的历史分析趋势
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.trend import TrendResponse
from app.services.trend_service import get_user_trends

router = APIRouter(prefix="/trends", tags=["纵向对比"])


@router.get("", response_model=TrendResponse)
async def get_trends(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrendResponse:
    return await get_user_trends(db, current_user.pseudonym_id)
