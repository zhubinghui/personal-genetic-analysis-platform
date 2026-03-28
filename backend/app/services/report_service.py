"""
报告生成服务

输出格式：
1. JSON（ReportData）— 供前端 SPA 使用
2. PDF（ReportLab）— 供用户下载存档，加密存入 MinIO
"""

import io
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisJob, AnalysisResult
from app.models.sample import Sample
from app.services.recommendation_engine import Recommendation, RecommendationEngine
from app.services.storage_service import StorageService
from app.config import settings


@dataclass
class ClockResults:
    horvath_age: float | None
    grimage_age: float | None
    phenoage_age: float | None
    dunedinpace: float | None
    chronological_age: int | None
    biological_age_acceleration: float | None


@dataclass
class QCSummary:
    qc_passed: bool | None
    n_probes_before: int | None
    n_probes_after: int | None


@dataclass
class ReportData:
    job_id: str
    generated_at: str
    summary: str
    clocks: ClockResults
    dimensions: dict | None
    recommendations: list[Recommendation]
    qc_summary: QCSummary
    benchmark: dict | None = None  # BenchmarkData 序列化后的 dict
    pdf_available: bool = False


class ReportService:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage
        self.rec_engine = RecommendationEngine()

    async def generate(self, job_id: uuid.UUID, db: AsyncSession) -> ReportData:
        # 加载分析结果
        res = await db.execute(
            select(AnalysisResult)
            .join(AnalysisJob, AnalysisResult.job_id == AnalysisJob.id)
            .where(AnalysisJob.id == job_id, AnalysisJob.status == "completed")
        )
        ar = res.scalar_one_or_none()
        if ar is None:
            raise ValueError(f"分析结果不存在或未完成: {job_id}")

        # 加载 pseudonym_id 用于存储路径
        sample_res = await db.execute(select(Sample).where(Sample.id == ar.sample_id))
        sample = sample_res.scalar_one_or_none()

        # 生成推荐（有维度数据时按维度生成；否则按综合评分生成通用建议）
        recommendations: list[Recommendation] = []
        if ar.dunedinpace:
            dims = ar.dunedinpace_dimensions or {}
            recommendations = self.rec_engine.generate(dims, ar.dunedinpace)

        # RAG 整合：从知识库检索相关文献附加到每条推荐
        try:
            from app.services.rag_service import enrich_recommendations
            await enrich_recommendations(db, recommendations)
        except Exception:
            pass  # 知识库查询失败不影响报告生成

        clocks = ClockResults(
            horvath_age=ar.horvath_age,
            grimage_age=ar.grimage_age,
            phenoage_age=ar.phenoage_age,
            dunedinpace=ar.dunedinpace,
            chronological_age=ar.chronological_age,
            biological_age_acceleration=ar.biological_age_acceleration,
        )

        summary = self._build_summary(clocks)

        # 同龄对标
        benchmark_data = None
        try:
            from app.services.benchmark_service import compute_benchmark
            bm = await compute_benchmark(db, ar)
            if bm:
                benchmark_data = bm.model_dump()
        except Exception:
            pass  # 对标计算失败不影响报告

        report = ReportData(
            job_id=str(job_id),
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            clocks=clocks,
            dimensions=ar.dunedinpace_dimensions,
            recommendations=recommendations,
            qc_summary=QCSummary(
                qc_passed=ar.qc_passed,
                n_probes_before=ar.n_probes_before,
                n_probes_after=ar.n_probes_after,
            ),
            benchmark=benchmark_data,
        )

        # 生成 PDF 并存入 MinIO
        if sample:
            try:
                pdf_bytes = self._render_pdf(report)
                await self.storage.upload_encrypted(
                    pseudonym_id=sample.pseudonym_id,
                    sample_id=sample.id,
                    file_bytes=pdf_bytes,
                    filename=f"report_{job_id}.pdf",
                    bucket=settings.minio_bucket_reports,
                )
                report.pdf_available = True
            except Exception:
                pass  # PDF 生成失败不影响 JSON 报告

        return report

    def _build_summary(self, clocks: ClockResults) -> str:
        pace = clocks.dunedinpace
        accel = clocks.biological_age_acceleration

        if pace is None:
            return "分析结果已生成，请查看各维度详情。"

        if pace < 0.9:
            headline = f"优秀：您的衰老速率比同龄人群慢 {(1 - pace) * 100:.0f}%。"
        elif pace > 1.1:
            headline = f"需要关注：您的衰老速率比同龄人群快 {(pace - 1) * 100:.0f}%。"
        else:
            headline = "正常：您的衰老速率接近人群平均水平。"

        accel_str = ""
        if accel is not None:
            direction = "超前" if accel > 0 else "滞后"
            accel_str = f" Horvath 生物学年龄比实际年龄{direction} {abs(accel):.1f} 岁。"

        return headline + accel_str

    def _render_pdf(self, report: ReportData) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        story = []

        # 标题
        title_style = ParagraphStyle(
            "Title", parent=styles["Title"], fontSize=18, spaceAfter=12
        )
        story.append(Paragraph("基因抗衰老分析报告", title_style))
        story.append(Paragraph(f"生成时间：{report.generated_at[:19].replace('T', ' ')}", styles["Normal"]))
        story.append(Spacer(1, 0.5 * cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#22c55e")))
        story.append(Spacer(1, 0.5 * cm))

        # 总结
        story.append(Paragraph("综合评估", styles["Heading2"]))
        story.append(Paragraph(report.summary, styles["Normal"]))
        story.append(Spacer(1, 0.5 * cm))

        # 时钟结果表格
        story.append(Paragraph("衰老时钟评分", styles["Heading2"]))
        c = report.clocks
        clock_data = [
            ["指标", "评分", "说明"],
            ["实际年龄", f"{c.chronological_age} 岁", ""],
            ["Horvath 生物学年龄", f"{c.horvath_age:.1f} 岁" if c.horvath_age else "N/A", "多组织表观遗传时钟"],
            ["GrimAge 生物学年龄", f"{c.grimage_age:.1f} 岁" if c.grimage_age else "N/A", "死亡率预测时钟"],
            ["PhenoAge 生物学年龄", f"{c.phenoage_age:.1f} 岁" if c.phenoage_age else "N/A", "临床表型整合时钟"],
            ["DunedinPACE 衰老速率", f"{c.dunedinpace:.3f}" if c.dunedinpace else "N/A", "1.0=平均，>1加速，<1减缓"],
            ["生物学年龄加速值", f"{c.biological_age_acceleration:+.1f} 岁" if c.biological_age_acceleration else "N/A", "Horvath 年龄 − 实际年龄"],
        ]
        t = Table(clock_data, colWidths=[5 * cm, 3.5 * cm, 8.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16a34a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0fdf4")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.7 * cm))

        # 推荐方案
        if report.recommendations:
            story.append(Paragraph("个性化抗衰老建议", styles["Heading2"]))
            story.append(Paragraph(
                "以下建议基于您的 DunedinPACE 维度评分和最新循证医学研究，按优先级排列。"
                "所有建议仅供健康管理参考，不构成医疗诊断。",
                styles["Normal"]
            ))
            story.append(Spacer(1, 0.3 * cm))

            for i, rec in enumerate(report.recommendations, 1):
                rec_style = ParagraphStyle(
                    f"Rec{i}",
                    parent=styles["Normal"],
                    leftIndent=10,
                    spaceAfter=4,
                )
                evidence_badge = {"A": "【A级证据】", "B": "【B级证据】", "C": "【C级证据】"}.get(
                    rec.evidence_level, ""
                )
                story.append(Paragraph(
                    f"<b>{i}. {rec.title}</b> {evidence_badge} "
                    f"（预计 {rec.timeframe_weeks} 周见效）",
                    styles["Heading3"]
                ))
                story.append(Paragraph(rec.summary, rec_style))
                if rec.pubmed_urls:
                    refs = " | ".join(
                        f'<a href="{url}" color="blue">PMID:{pmid}</a>'
                        for pmid, url in zip(rec.pmids, rec.pubmed_urls)
                    )
                    story.append(Paragraph(f"参考文献：{refs}", rec_style))

                # 知识库文献支撑
                if rec.literature_references:
                    lit_style = ParagraphStyle(
                        f"Lit{i}",
                        parent=styles["Normal"],
                        leftIndent=16,
                        fontSize=7.5,
                        textColor=colors.HexColor("#4b5563"),
                        spaceAfter=2,
                    )
                    story.append(Paragraph(
                        "<i>知识库文献支撑：</i>",
                        ParagraphStyle("LitH", parent=lit_style, textColor=colors.HexColor("#059669")),
                    ))
                    for lit in rec.literature_references:
                        page_str = f" (p.{lit.page_number})" if lit.page_number else ""
                        score_pct = f"{lit.relevance_score * 100:.0f}%"
                        # 截断 excerpt 以免撑爆 PDF
                        excerpt = lit.excerpt[:200] + "..." if len(lit.excerpt) > 200 else lit.excerpt
                        story.append(Paragraph(
                            f"<b>{lit.document_title}</b>{page_str} "
                            f"[相关度 {score_pct}]  {excerpt}",
                            lit_style,
                        ))

                story.append(Spacer(1, 0.2 * cm))

        # 免责声明
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        disclaimer_style = ParagraphStyle(
            "Disclaimer", parent=styles["Normal"], fontSize=7, textColor=colors.grey
        )
        story.append(Paragraph(
            "免责声明：本报告基于 DNA 甲基化数据的计算分析，仅供健康管理参考，"
            "不构成医疗诊断、治疗建议或处方。如有健康问题请咨询专业医生。",
            disclaimer_style
        ))

        doc.build(story)
        return buffer.getvalue()
