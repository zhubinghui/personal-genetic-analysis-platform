"""
Chatbot 对话 API — 基于知识库 + 分析结果的 RAG 问答

端点：
  POST /api/v1/chat — 发送问题，返回 AI 回答 + 引用来源
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.analysis import AnalysisJob, AnalysisResult
from app.models.sample import Sample
from app.models.user import User
from app.services.knowledge_service import semantic_search
from app.services.llm_service import get_llm_provider

router = APIRouter(prefix="/chat", tags=["Chatbot 对话"])

SYSTEM_PROMPT = """你是一位专业的衰老研究专家和健康管理顾问。你的任务是基于用户的基因甲基化分析结果和科学文献，为用户提供通俗易懂的解读和建议。

规则：
1. 用中文回答，语气亲切专业
2. 引用文献时标注来源
3. 始终提醒用户分析结果仅供参考，不构成医疗诊断
4. 如果知识库中没有相关信息，诚实说明而非编造
5. 回答要具体、可操作，避免空泛的建议"""


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    job_id: str | None = None  # 关联分析任务（可选）


class ChatSource(BaseModel):
    document_title: str
    page_number: int | None
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatResponse:
    # 1. 获取 LLM Provider
    llm = await get_llm_provider(db)
    if llm is None:
        raise HTTPException(status_code=503, detail="AI 对话功能未配置，请联系管理员设置 LLM")

    # 2. 检索知识库相关文献
    search_results = []
    try:
        search_results = await semantic_search(db, query=body.query, top_k=5, score_threshold=0.3)
    except Exception:
        pass

    # 3. 加载分析结果上下文（如果有 job_id）
    analysis_context = ""
    if body.job_id:
        try:
            job_uuid = uuid.UUID(body.job_id)
            result = await db.execute(
                select(AnalysisResult)
                .join(AnalysisJob, AnalysisResult.job_id == AnalysisJob.id)
                .join(Sample, AnalysisResult.sample_id == Sample.id)
                .where(
                    AnalysisJob.id == job_uuid,
                    Sample.pseudonym_id == current_user.pseudonym_id,
                )
            )
            ar = result.scalar_one_or_none()
            if ar:
                analysis_context = _format_analysis_context(ar)
        except Exception:
            pass

    # 4. 构建 prompt
    context_parts = []
    if analysis_context:
        context_parts.append(f"## 用户的分析结果\n{analysis_context}")
    if search_results:
        lit_text = "\n\n".join(
            f"[{r.document_title}] (p.{r.page_number or '?'}, 相关度{r.score:.0%})\n{r.chunk_text[:500]}"
            for r in search_results
        )
        context_parts.append(f"## 相关文献\n{lit_text}")

    context = "\n\n".join(context_parts) if context_parts else "（知识库暂无相关内容）"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"参考资料：\n{context}\n\n用户问题：{body.query}"},
    ]

    # 5. 调用 LLM
    try:
        answer = await llm.chat(messages, temperature=0.4, max_tokens=2000)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 回答生成失败: {str(e)[:200]}")

    # 6. 构建来源列表
    sources = [
        ChatSource(
            document_title=r.document_title,
            page_number=r.page_number,
            relevance_score=r.score,
        )
        for r in search_results
    ]

    return ChatResponse(answer=answer, sources=sources)


def _format_analysis_context(ar: AnalysisResult) -> str:
    """将分析结果格式化为 LLM 可读的上下文。"""
    lines = [f"实际年龄: {ar.chronological_age} 岁"]
    if ar.horvath_age:
        lines.append(f"Horvath 生物学年龄: {ar.horvath_age:.1f} 岁")
    if ar.grimage_age:
        lines.append(f"GrimAge 生物学年龄: {ar.grimage_age:.1f} 岁")
    if ar.phenoage_age:
        lines.append(f"PhenoAge 生物学年龄: {ar.phenoage_age:.1f} 岁")
    if ar.dunedinpace:
        pace_desc = "减缓" if ar.dunedinpace < 1 else "加速" if ar.dunedinpace > 1 else "平均"
        lines.append(f"DunedinPACE 衰老速率: {ar.dunedinpace:.3f}（{pace_desc}）")
    if ar.biological_age_acceleration:
        direction = "年轻" if ar.biological_age_acceleration < 0 else "衰老"
        lines.append(f"年龄加速值: {ar.biological_age_acceleration:+.1f} 岁（比实际年龄{direction}）")
    if ar.dunedinpace_dimensions:
        lines.append("DunedinPACE 维度分项：")
        for system, metrics in ar.dunedinpace_dimensions.items():
            if isinstance(metrics, dict):
                vals = [v for v in metrics.values() if v is not None]
                if vals:
                    avg = sum(vals) / len(vals)
                    status = "正常" if avg < 1.1 else "偏高" if avg < 1.3 else "高风险"
                    lines.append(f"  {system}: {avg:.3f}（{status}）")
    return "\n".join(lines)
