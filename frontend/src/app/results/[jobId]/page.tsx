"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { reportApi, jobApi, ApiError } from "@/lib/api";
import { useAnalysisJob } from "@/lib/hooks/useAnalysisJob";
import AgeClockGauge from "@/components/charts/AgeClockGauge";
import DunedinPaceRadar from "@/components/charts/DunedinPaceRadar";
import AgingDimensionBars from "@/components/charts/AgingDimensionBars";
import RecommendationCard from "@/components/report/RecommendationCard";
import CohortBenchmark from "@/components/report/CohortBenchmark";
import { TermLabel } from "@/components/ui/InfoTip";
import type { ReportData } from "@/types";

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();
  const { job, error: pollError } = useAnalysisJob(jobId);
  const [report, setReport] = useState<ReportData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (job?.status === "completed") {
      reportApi.get(jobId).then(setReport).catch((e) => {
        setError(e instanceof ApiError ? e.message : "加载报告失败");
      });
    }
  }, [job?.status, jobId]);

  if (error || pollError) {
    const msg = error || pollError || "加载失败";
    const isAuth = msg.includes("过期") || msg.includes("无效") || msg.includes("令牌");
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-3">
          <p className="text-red-500">{msg}</p>
          {isAuth ? (
            <Link href="/login" className="text-brand-600 hover:underline text-sm">
              重新登录
            </Link>
          ) : (
            <Link href="/dashboard" className="text-brand-600 hover:underline text-sm">
              返回控制台
            </Link>
          )}
        </div>
      </div>
    );
  }

  if (!job || job.status === "queued" || job.status === "running") {
    return (
      <div className="min-h-screen flex items-center justify-center gradient-brand">
        <div className="text-center space-y-4">
          <div className="w-14 h-14 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="font-semibold text-gray-700 text-lg">分析进行中...</p>
          <p className="text-sm text-gray-500">
            当前阶段：<span className="font-medium text-brand-600">{job?.stage ?? "队列中"}</span> · 通常需要 5-20 分钟
          </p>
          <p className="text-xs text-gray-400">每 5 秒自动刷新</p>
        </div>
      </div>
    );
  }

  if (job.status === "failed") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <span className="text-red-500 text-xl">!</span>
          </div>
          <p className="text-red-500 font-medium">分析失败</p>
          <p className="text-sm text-gray-500 max-w-sm">{job.error_message ?? "未知错误"}</p>
          <Link href="/upload" className="inline-block text-brand-600 hover:underline text-sm">
            重新上传
          </Link>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const { clocks, dimensions, recommendations, summary } = report;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between shadow-sm">
        <Link href="/dashboard" className="text-brand-600 hover:underline text-sm">
          ← 返回控制台
        </Link>
        <div className="flex gap-3">
          <Link
            href="/trends"
            className="px-4 py-2 border border-brand-200 text-brand-600 rounded-lg text-sm hover:bg-brand-50 transition"
          >
            📈 历史对比
          </Link>
          {report.pdf_available && (
            <a
              href={reportApi.pdfUrl(jobId)}
              className="px-4 py-2 bg-brand-600 text-white rounded-lg text-sm hover:bg-brand-700 transition shadow-sm"
            >
              下载 PDF 报告
            </a>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto py-8 px-4 space-y-6">
        {/* 综合评估 */}
        <div className="card gradient-brand p-6">
          <h1 className="text-xl font-bold text-gray-800 mb-2">
            <TermLabel term="epigenetics">衰老分析报告</TermLabel>
          </h1>
          <p className="text-gray-600 leading-relaxed">{summary}</p>
          <p className="text-xs text-gray-400 mt-3">
            生成时间：{new Date(report.generated_at).toLocaleString("zh-CN")}
          </p>
        </div>

        {/* 时钟对比 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <AgeClockGauge
            horvathAge={clocks.horvath_age}
            grimAge={clocks.grimage_age}
            phenoAge={clocks.phenoage_age}
            chronologicalAge={clocks.chronological_age}
          />
          {dimensions && clocks.dunedinpace && (
            <DunedinPaceRadar dimensions={dimensions} paceScore={clocks.dunedinpace} />
          )}
        </div>

        {/* 关键指标卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "实际年龄", term: undefined, value: clocks.chronological_age ? `${clocks.chronological_age} 岁` : "N/A", color: "text-gray-800" },
            { label: "Horvath 生物学年龄", term: "horvath", value: clocks.horvath_age ? `${clocks.horvath_age.toFixed(1)} 岁` : "N/A", color: "text-blue-600" },
            { label: "DunedinPACE", term: "dunedinpace", value: clocks.dunedinpace ? clocks.dunedinpace.toFixed(3) : "N/A", color: clocks.dunedinpace && clocks.dunedinpace > 1.1 ? "text-red-500" : "text-green-600" },
            {
              label: "年龄加速值", term: "age_acceleration",
              value: clocks.biological_age_acceleration != null ? `${clocks.biological_age_acceleration > 0 ? "+" : ""}${clocks.biological_age_acceleration.toFixed(1)} 岁` : "N/A",
              color: clocks.biological_age_acceleration != null && clocks.biological_age_acceleration > 0 ? "text-orange-500" : "text-green-600",
            },
          ].map((item) => (
            <div key={item.label} className="card p-4 text-center">
              <p className={`text-2xl metric-value ${item.color}`}>{item.value}</p>
              <p className="text-xs text-gray-400 mt-1.5">
                <TermLabel term={item.term}>{item.label}</TermLabel>
              </p>
            </div>
          ))}
        </div>

        {/* 同龄人群对标 */}
        {report.benchmark && <CohortBenchmark benchmark={report.benchmark} />}

        {/* 19 维度条形图 */}
        {dimensions && <AgingDimensionBars dimensions={dimensions} />}

        {/* 推荐建议 */}
        {recommendations.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-800">
              抗衰老建议（{recommendations.length} 条）
            </h2>
            <p className="text-sm text-gray-500">
              {recommendations[0]?.dimension?.startsWith("general.")
                ? "基于您的 DunedinPACE 综合评分生成的循证维护建议，按优先级排序"
                : "基于您的 DunedinPACE 维度评分匹配，按优先级和风险程度排序"}
            </p>
            {recommendations.map((rec, i) => (
              <RecommendationCard key={i} rec={rec} />
            ))}
          </div>
        )}

        {/* 免责声明 */}
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <p className="text-xs text-amber-700 leading-relaxed">
            <strong>免责声明：</strong>
            本报告基于 <TermLabel term="dna_methylation">DNA 甲基化</TermLabel> 数据的计算分析，仅供健康管理参考，不构成医疗诊断或治疗建议。
            DunedinPACE 维度解读基于模型特征贡献推断，不代表实测生化指标。
            如有健康问题请咨询专业医生。
          </p>
        </div>
      </main>
    </div>
  );
}
