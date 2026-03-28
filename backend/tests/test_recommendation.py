"""推荐引擎单元测试"""

import pytest

from app.services.recommendation_engine import RecommendationEngine


@pytest.fixture
def engine():
    return RecommendationEngine()


class TestRecommendationGeneration:
    def test_exceeding_threshold_generates_recs(self, engine: RecommendationEngine):
        """超阈值维度应生成对应推荐。"""
        dims = {"cardiovascular": {"blood_pressure": 1.3, "cholesterol": 0.8}}
        recs = engine.generate(dims, pace_score=1.2)
        assert len(recs) > 0
        assert any(r.dimension == "cardiovascular.blood_pressure" for r in recs)

    def test_below_threshold_skipped(self, engine: RecommendationEngine):
        """低于阈值的维度不应生成推荐。"""
        dims = {"cardiovascular": {"blood_pressure": 0.8, "cholesterol": 0.9}}
        recs = engine.generate(dims, pace_score=0.85)
        # 无超阈值维度 → 应回退到通用推荐
        assert all(r.dimension.startswith("general.") for r in recs)

    def test_general_fallback(self, engine: RecommendationEngine):
        """无维度数据时应返回通用维护建议。"""
        recs = engine.generate({}, pace_score=0.9)
        assert len(recs) > 0
        assert all(r.dimension.startswith("general.") for r in recs)

    def test_null_dimensions_fallback(self, engine: RecommendationEngine):
        """维度值全部为 None 时回退到通用建议。"""
        dims = {"cardiovascular": {"blood_pressure": None, "cholesterol": None}}
        recs = engine.generate(dims, pace_score=1.0)
        assert len(recs) > 0
        assert all(r.dimension.startswith("general.") for r in recs)

    def test_max_recommendations_limit(self, engine: RecommendationEngine):
        """应遵守最大推荐数量限制。"""
        # 多个维度超阈值
        dims = {
            "cardiovascular": {"blood_pressure": 1.5, "cholesterol": 1.4, "triglycerides": 1.3},
            "metabolic": {"hba1c": 1.4, "bmi": 1.3},
            "immune": {"crp": 1.5, "wbc": 1.3},
        }
        recs = engine.generate(dims, pace_score=1.3, max_recommendations=3)
        assert len(recs) <= 3

    def test_sorted_by_priority_then_score(self, engine: RecommendationEngine):
        """推荐应按 (priority ASC, dimension_score DESC) 排序。"""
        dims = {
            "cardiovascular": {"blood_pressure": 1.5},
            "metabolic": {"hba1c": 1.8},
        }
        recs = engine.generate(dims, pace_score=1.3)
        if len(recs) >= 2:
            for i in range(len(recs) - 1):
                a, b = recs[i], recs[i + 1]
                assert (a.priority, -a.dimension_score) <= (b.priority, -b.dimension_score)


class TestRecommendationFields:
    def test_pubmed_urls_generated(self, engine: RecommendationEngine):
        """每条推荐应自动生成 PubMed URL。"""
        recs = engine.generate({}, pace_score=1.0)
        for rec in recs:
            assert len(rec.pubmed_urls) == len(rec.pmids)
            for url in rec.pubmed_urls:
                assert url.startswith("https://pubmed.ncbi.nlm.nih.gov/")

    def test_required_fields_present(self, engine: RecommendationEngine):
        """每条推荐应包含所有必需字段。"""
        recs = engine.generate({}, pace_score=1.0)
        for rec in recs:
            assert rec.title
            assert rec.summary
            assert rec.evidence_level in ("A", "B", "C")
            assert rec.category in ("diet", "exercise", "supplement", "lifestyle")
            assert rec.timeframe_weeks > 0
            assert rec.priority > 0

    def test_literature_references_default_empty(self, engine: RecommendationEngine):
        """RAG 未执行时 literature_references 应为空列表。"""
        recs = engine.generate({}, pace_score=1.0)
        for rec in recs:
            assert rec.literature_references == []
