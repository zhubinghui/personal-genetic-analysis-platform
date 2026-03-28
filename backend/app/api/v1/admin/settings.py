"""
管理员系统设置 API

端点：
  GET  /admin/settings/llm          — 获取 LLM 配置
  PUT  /admin/settings/llm          — 更新 LLM 配置
  POST /admin/settings/llm/test     — 测试 LLM 连接
  GET  /admin/settings/vectorization — 获取向量化配置
  PUT  /admin/settings/vectorization — 更新向量化配置
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_admin_user
from app.database import get_db
from app.models.knowledge import KnowledgeDocument
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


# ── 向量化设置 ────────────────────────────────────────────────

class VectorizationSettingsResponse(BaseModel):
    embedding_workers: int
    current_pool_size: int
    pending_documents: int
    processing_documents: int


class VectorizationSettingsRequest(BaseModel):
    embedding_workers: int = 2


@router.get("/vectorization", response_model=VectorizationSettingsResponse)
async def get_vectorization_settings(
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.services.knowledge_service import EMBEDDING_WORKERS, _embedding_pool
    from sqlalchemy import func as sa_func

    # 从 DB 读取配置（如果有）
    result = await db.execute(
        select(SystemSettings).where(
            SystemSettings.category == "vectorization",
            SystemSettings.key == "embedding_workers",
        )
    )
    row = result.scalar_one_or_none()
    configured = int(row.value) if row else EMBEDDING_WORKERS

    # 统计当前文档状态
    pending = (await db.execute(
        select(sa_func.count()).select_from(KnowledgeDocument)
        .where(KnowledgeDocument.status == "pending")
    )).scalar_one()
    processing = (await db.execute(
        select(sa_func.count()).select_from(KnowledgeDocument)
        .where(KnowledgeDocument.status == "processing")
    )).scalar_one()

    return VectorizationSettingsResponse(
        embedding_workers=configured,
        current_pool_size=_embedding_pool._max_workers if _embedding_pool else EMBEDDING_WORKERS,
        pending_documents=pending,
        processing_documents=processing,
    )


@router.put("/vectorization")
async def update_vectorization_settings(
    body: VectorizationSettingsRequest,
    _: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if body.embedding_workers < 1 or body.embedding_workers > 8:
        raise HTTPException(status_code=400, detail="Worker 数量范围: 1-8")

    # 保存到 DB
    result = await db.execute(
        select(SystemSettings).where(
            SystemSettings.category == "vectorization",
            SystemSettings.key == "embedding_workers",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.value = str(body.embedding_workers)
    else:
        db.add(SystemSettings(category="vectorization", key="embedding_workers", value=str(body.embedding_workers)))
    await db.commit()

    # 动态重建进程池
    from app.services.knowledge_service import _embedding_pool, EMBEDDING_WORKERS
    import app.services.knowledge_service as ks
    if _embedding_pool is not None:
        _embedding_pool.shutdown(wait=False)
    from concurrent.futures import ProcessPoolExecutor
    ks._embedding_pool = ProcessPoolExecutor(max_workers=body.embedding_workers)
    ks.EMBEDDING_WORKERS = body.embedding_workers

    return {"message": f"向量化进程池已调整为 {body.embedding_workers} workers"}
