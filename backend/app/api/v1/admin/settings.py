"""
管理员系统设置 API

端点：
  GET  /admin/settings/llm      — 获取 LLM 配置
  PUT  /admin/settings/llm      — 更新 LLM 配置
  POST /admin/settings/llm/test — 测试 LLM 连接
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_admin_user
from app.database import get_db
from app.models.settings import SystemSettings
from app.models.user import User
from app.services.llm_service import PROVIDER_DEFAULTS, LLMConfig, create_provider, get_llm_config_from_db

router = APIRouter(prefix="/admin/settings", tags=["管理员-系统设置"])


class LLMSettingsRequest(BaseModel):
    provider: str = ""       # claude / openai / deepseek / kimi
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    temperature: float = 0.3
    max_tokens: int = 2000


class LLMSettingsResponse(BaseModel):
    provider: str
    api_key_masked: str  # 脱敏显示
    model: str
    base_url: str
    temperature: float
    max_tokens: int
    available_providers: list[dict]


@router.get("/llm", response_model=LLMSettingsResponse)
async def get_llm_settings(
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    config = await get_llm_config_from_db(db)
    # API Key 脱敏
    masked = ""
    if config.api_key:
        masked = config.api_key[:8] + "..." + config.api_key[-4:] if len(config.api_key) > 12 else "****"

    return LLMSettingsResponse(
        provider=config.provider,
        api_key_masked=masked,
        model=config.model or PROVIDER_DEFAULTS.get(config.provider, {}).get("model", ""),
        base_url=config.base_url or PROVIDER_DEFAULTS.get(config.provider, {}).get("base_url", ""),
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        available_providers=[
            {"name": k, "default_model": v["model"], "default_base_url": v.get("base_url", "")}
            for k, v in PROVIDER_DEFAULTS.items()
        ],
    )


@router.put("/llm")
async def update_llm_settings(
    body: LLMSettingsRequest,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    settings_map = {
        "provider": body.provider,
        "api_key": body.api_key,
        "model": body.model,
        "base_url": body.base_url,
        "temperature": str(body.temperature),
        "max_tokens": str(body.max_tokens),
    }

    for key, value in settings_map.items():
        result = await db.execute(
            select(SystemSettings).where(
                SystemSettings.category == "llm",
                SystemSettings.key == key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            db.add(SystemSettings(category="llm", key=key, value=value))

    await db.commit()
    return {"message": "LLM 设置已保存"}


@router.post("/llm/test")
async def test_llm_connection(
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """测试当前 LLM 配置是否可用。"""
    config = await get_llm_config_from_db(db)
    provider = create_provider(config)

    if provider is None:
        raise HTTPException(status_code=400, detail="LLM 未配置，请先设置 Provider 和 API Key")

    try:
        response = await provider.chat(
            messages=[
                {"role": "system", "content": "You are a test bot."},
                {"role": "user", "content": "Reply with exactly: OK"},
            ],
            temperature=0,
            max_tokens=10,
        )
        return {"status": "ok", "response": response.strip(), "provider": config.provider, "model": config.model}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM 连接失败: {str(e)[:200]}")
