"""
循证抗衰老推荐引擎

基于 DunedinPACE 19 维度分项评分，生成优先级排序的个性化干预建议。
每条推荐含 PubMed 文献引用，证据等级基于 GRADE 标准。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "recommendations.json"


@dataclass
class LiteratureReference:
    """知识库文献引用（由 RAG 服务填充）"""
    document_title: str
    excerpt: str            # chunk_text 截取前 300 字符
    page_number: int | None
    relevance_score: float  # 余弦相似度 0~1


@dataclass
class Recommendation:
    dimension: str
    dimension_score: float
    priority: int
    title: str
    summary: str
    evidence_level: str  # "A", "B", "C"
    pmids: list[str]
    category: str  # "diet", "exercise", "supplement", "lifestyle"
    timeframe_weeks: int
    pubmed_urls: list[str] = field(default_factory=list)
    literature_references: list[LiteratureReference] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.pubmed_urls = [
            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            for pmid in self.pmids
        ]


# 通用维护建议（当维度评分均为 null 或无超阈指标时触发）
_GENERAL_RECS: list[dict] = [
    {
        "dimension": "general.pace",
        "priority": 2,
        "title": "间歇性禁食（16:8 方案）",
        "summary": "每日将进食窗口限制在 8 小时内（如 12:00–20:00），研究表明可降低 Horvath 甲基化年龄加速约 2.4 年，并改善代谢标志物。",
        "evidence_level": "B",
        "pmids": ["31641963", "34649080"],
        "category": "diet",
        "timeframe_weeks": 12,
    },
    {
        "dimension": "general.pace",
        "priority": 2,
        "title": "地中海饮食模式",
        "summary": "富含橄榄油、蔬菜、鱼类和坚果的饮食模式与更低的 DunedinPACE 评分（衰老更慢）和表观遗传时钟减缓显著相关，可维持现有良好衰老轨迹。",
        "evidence_level": "A",
        "pmids": ["23704726", "33574180", "33574194"],
        "category": "diet",
        "timeframe_weeks": 8,
    },
    {
        "dimension": "general.pace",
        "priority": 1,
        "title": "有氧 + 抗阻联合训练",
        "summary": "每周 ≥150 分钟中等强度有氧运动配合 2 次抗阻训练，Meta 分析显示可将 Horvath 生物学年龄减缓 1.5–3 年，同时维持 DunedinPACE 低值。",
        "evidence_level": "A",
        "pmids": ["31504075", "28467327", "35354048"],
        "category": "exercise",
        "timeframe_weeks": 16,
    },
    {
        "dimension": "general.pace",
        "priority": 3,
        "title": "优化睡眠质量（7–9 小时）",
        "summary": "睡眠时长 < 6 小时或 > 9 小时均与 DunedinPACE 加速相关。保持规律作息、减少蓝光暴露和睡前刺激，可维持良好的表观遗传衰老状态。",
        "evidence_level": "B",
        "pmids": ["30403239", "34489420"],
        "category": "lifestyle",
        "timeframe_weeks": 4,
    },
    {
        "dimension": "general.pace",
        "priority": 3,
        "title": "心理压力管理（正念冥想）",
        "summary": "慢性压力通过皮质醇等途径加速表观遗传衰老；每日 10–20 分钟正念冥想可显著降低炎症标志物，有助于维持低 DunedinPACE。",
        "evidence_level": "B",
        "pmids": ["30787473", "32053639"],
        "category": "lifestyle",
        "timeframe_weeks": 8,
    },
    {
        "dimension": "general.pace",
        "priority": 4,
        "title": "减少超加工食品摄入",
        "summary": "超加工食品（UPF）与表观遗传年龄加速独立相关。将 UPF 占热量比例降至 < 20% 可显著降低多个甲基化时钟评分。",
        "evidence_level": "B",
        "pmids": ["34284344", "35090879"],
        "category": "diet",
        "timeframe_weeks": 8,
    },
    {
        "dimension": "general.pace",
        "priority": 4,
        "title": "维生素 D 充足化",
        "summary": "维生素 D 缺乏（< 20 ng/mL）与 Horvath、GrimAge 加速相关。日晒或补充 2000–4000 IU/天，使血清 25(OH)D 维持 40–60 ng/mL。",
        "evidence_level": "B",
        "pmids": ["28490607", "31815768"],
        "category": "supplement",
        "timeframe_weeks": 12,
    },
]


class RecommendationEngine:
    def __init__(self) -> None:
        with open(DATA_FILE, encoding="utf-8") as f:
            self._data: dict = json.load(f)

    def generate(
        self,
        dimensions: dict,
        pace_score: float,
        max_recommendations: int = 10,
    ) -> list[Recommendation]:
        """
        根据 DunedinPACE 维度评分生成推荐列表。
        当所有维度评分均为 null 或均未超阈值时，自动追加通用维护建议。
        """
        recommendations: list[Recommendation] = []

        # 扁平化维度：{category}.{metric} -> score
        flat: dict[str, float] = {}
        for category, metrics in dimensions.items():
            if isinstance(metrics, dict):
                for metric, score in metrics.items():
                    if score is not None:
                        flat[f"{category}.{metric}"] = float(score)

        for key, score in flat.items():
            if key not in self._data:
                continue
            entry = self._data[key]
            if score <= entry.get("threshold_high", 1.1):
                continue  # 未超阈值，无需推荐

            for rec_data in entry.get("recommendations", []):
                recommendations.append(
                    Recommendation(
                        dimension=key,
                        dimension_score=score,
                        priority=rec_data["priority"],
                        title=rec_data["title"],
                        summary=rec_data["summary"],
                        evidence_level=rec_data["evidence_level"],
                        pmids=rec_data["pmids"],
                        category=rec_data["category"],
                        timeframe_weeks=rec_data["timeframe_weeks"],
                    )
                )

        # 排序：优先级升序，维度评分降序（高风险优先）
        recommendations.sort(key=lambda r: (r.priority, -r.dimension_score))

        # 无维度数据或无超阈指标时，追加通用维护建议
        if not recommendations:
            recommendations = self._generate_general(pace_score)

        return recommendations[:max_recommendations]

    def _generate_general(self, pace_score: float) -> list[Recommendation]:
        """当无分项超阈值时，返回基于综合评分的通用维护/优化建议。"""
        recs = []
        for rec_data in _GENERAL_RECS:
            recs.append(
                Recommendation(
                    dimension=rec_data["dimension"],
                    dimension_score=pace_score,
                    priority=rec_data["priority"],
                    title=rec_data["title"],
                    summary=rec_data["summary"],
                    evidence_level=rec_data["evidence_level"],
                    pmids=rec_data["pmids"],
                    category=rec_data["category"],
                    timeframe_weeks=rec_data["timeframe_weeks"],
                )
            )
        recs.sort(key=lambda r: (r.priority, -r.dimension_score))
        return recs
