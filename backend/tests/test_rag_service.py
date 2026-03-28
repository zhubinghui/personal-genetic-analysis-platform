"""RAG 服务单元测试"""

import pytest

from app.services.rag_service import _build_query
from app.services.recommendation_engine import Recommendation


def _make_rec(dimension: str = "cardiovascular.blood_pressure",
              title: str = "DASH Diet",
              category: str = "diet") -> Recommendation:
    return Recommendation(
        dimension=dimension,
        dimension_score=1.3,
        priority=1,
        title=title,
        summary="A heart-healthy diet.",
        evidence_level="A",
        pmids=["12345678"],
        category=category,
        timeframe_weeks=8,
    )


class TestQueryGeneration:
    def test_cardiovascular_context(self):
        rec = _make_rec("cardiovascular.blood_pressure")
        query = _build_query(rec)
        assert "cardiovascular" in query
        assert "blood pressure" in query
        assert "DNA methylation" in query

    def test_metabolic_context(self):
        rec = _make_rec("metabolic.hba1c", "Glycemic Control")
        query = _build_query(rec)
        assert "metabolic" in query.lower()
        assert "glucose" in query.lower() or "insulin" in query.lower()
        assert "Glycemic Control" in query

    def test_general_dimension(self):
        rec = _make_rec("general.pace", "Intermittent Fasting")
        query = _build_query(rec)
        assert "DunedinPACE" in query or "epigenetic" in query.lower()

    def test_exercise_category_context(self):
        rec = _make_rec(category="exercise")
        query = _build_query(rec)
        assert "exercise" in query.lower() or "training" in query.lower()

    def test_unknown_dimension_fallback(self):
        """未知维度应使用通用上下文，不报错。"""
        rec = _make_rec("unknown.dimension")
        query = _build_query(rec)
        assert "epigenetic" in query.lower()
        assert len(query) > 20  # 不应为空


class TestEnrichRecommendations:
    async def test_empty_list_noop(self, db):
        """空推荐列表应直接返回。"""
        from app.services.rag_service import enrich_recommendations
        recs: list[Recommendation] = []
        await enrich_recommendations(db, recs)
        assert recs == []

    async def test_graceful_on_empty_kb(self, db):
        """知识库为空时应返回空引用而非报错。"""
        from app.services.rag_service import enrich_recommendations
        recs = [_make_rec()]
        await enrich_recommendations(db, recs)
        assert recs[0].literature_references == []
