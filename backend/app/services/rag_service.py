"""
RAG 编排服务

将知识库向量搜索整合到报告推荐中：
  1. 根据每条 Recommendation 的维度 + 标题生成语义查询
  2. 调用 pgvector 余弦相似度搜索
  3. 将匹配的文献片段附加到推荐的 literature_references 中
  4. 知识库为空时静默跳过（graceful degradation）
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_service import semantic_search
from app.services.recommendation_engine import LiteratureReference, Recommendation

logger = logging.getLogger(__name__)

# 维度 → 英文上下文关键词映射（与 BAAI/bge-small-en-v1.5 英文嵌入模型对齐）
_DIMENSION_CONTEXT: dict[str, str] = {
    "cardiovascular": "cardiovascular aging blood pressure heart vascular endothelial",
    "metabolic":      "metabolic aging glucose insulin HbA1c diabetes obesity",
    "renal":          "renal aging kidney function glomerular filtration BUN creatinine",
    "hepatic":        "hepatic aging liver function ALT AST fibrosis",
    "pulmonary":      "pulmonary aging lung function FEV1 respiratory capacity",
    "immune":         "immune aging inflammation CRP white blood cells immunosenescence",
    "periodontal":    "periodontal aging gum disease oral health attachment loss",
    "cognitive":      "cognitive aging brain function memory neurodegeneration",
    "physical":       "physical aging muscle strength grip sarcopenia balance",
    "general":        "biological aging epigenetic clock DunedinPACE longevity",
}

# 推荐类别 → 附加搜索关键词
_CATEGORY_CONTEXT: dict[str, str] = {
    "diet":       "diet nutrition dietary intervention",
    "exercise":   "exercise physical activity training",
    "supplement": "supplementation vitamin nutrient",
    "lifestyle":  "lifestyle sleep stress management",
}


def _build_query(rec: Recommendation) -> str:
    """根据推荐内容构造英文语义搜索查询。"""
    # 提取维度大类
    dim_category = rec.dimension.split(".")[0] if "." in rec.dimension else rec.dimension
    dim_context = _DIMENSION_CONTEXT.get(dim_category, _DIMENSION_CONTEXT["general"])
    cat_context = _CATEGORY_CONTEXT.get(rec.category, "")

    # 组合：推荐标题关键词 + 维度上下文 + 类别上下文 + 领域锚点
    return f"{rec.title} {dim_context} {cat_context} DNA methylation epigenetic".strip()


async def enrich_recommendations(
    db: AsyncSession,
    recommendations: list[Recommendation],
    max_refs_per_rec: int = 3,
    score_threshold: float = 0.35,
) -> None:
    """
    为推荐列表中的每条建议检索知识库相关文献。

    直接修改 Recommendation 对象的 literature_references 字段（in-place）。
    知识库无文档或搜索无结果时静默跳过。
    """
    if not recommendations:
        return

    for rec in recommendations:
        try:
            query = _build_query(rec)
            results = await semantic_search(
                db,
                query=query,
                top_k=max_refs_per_rec,
                score_threshold=score_threshold,
            )

            rec.literature_references = [
                LiteratureReference(
                    document_title=r.document_title,
                    excerpt=r.chunk_text[:300] + ("..." if len(r.chunk_text) > 300 else ""),
                    page_number=r.page_number,
                    relevance_score=r.score,
                )
                for r in results
            ]

        except Exception as e:
            # 知识库查询失败不应阻断报告生成
            logger.warning("RAG 检索失败 (recommendation=%s): %s", rec.title, e)
            rec.literature_references = []
