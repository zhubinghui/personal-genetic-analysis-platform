"use client";

import type { BenchmarkData, BenchmarkMetric } from "@/types";
import { TermLabel } from "@/components/ui/InfoTip";

const METRIC_LABELS: { key: keyof Pick<BenchmarkData, "dunedinpace" | "horvath_acceleration" | "grimage_acceleration" | "phenoage_acceleration">; label: string; term: string; unit: string }[] = [
  { key: "dunedinpace", label: "DunedinPACE 衰老速率", term: "dunedinpace", unit: "" },
  { key: "horvath_acceleration", label: "Horvath 年龄加速", term: "horvath", unit: "岁" },
  { key: "grimage_acceleration", label: "GrimAge 年龄加速", term: "grimage", unit: "岁" },
  { key: "phenoage_acceleration", label: "PhenoAge 年龄加速", term: "phenoage", unit: "岁" },
];

function PercentileBar({ metric, label, term, unit }: { metric: BenchmarkMetric; label: string; term?: string; unit: string }) {
  const pct = metric.percentile;
  if (pct == null || metric.value == null) return null;

  const isGood = pct >= 50;
  const barColor = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-500";
  const textColor = pct >= 70 ? "text-green-600" : pct >= 40 ? "text-yellow-600" : "text-red-600";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <TermLabel term={term} className="text-gray-600">{label}</TermLabel>
        <span className={`font-semibold ${textColor}`}>
          优于 {pct.toFixed(0)}% 同龄人
        </span>
      </div>
      <div className="relative h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 ${barColor} rounded-full transition-all duration-700`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
        {/* 50% 基准线 */}
        <div className="absolute inset-y-0 left-1/2 w-px bg-gray-300" />
      </div>
      <div className="flex justify-between text-xs text-gray-400">
        <span>
          您: {metric.value.toFixed(metric.value % 1 ? 2 : 0)}{unit}
        </span>
        <span>
          同龄均值: {metric.cohort_mean?.toFixed(2) ?? "—"}{unit}
          {metric.cohort_std != null && ` (±${metric.cohort_std.toFixed(2)})`}
        </span>
      </div>
    </div>
  );
}

export default function CohortBenchmark({ benchmark }: { benchmark: BenchmarkData }) {
  return (
    <div className="bg-white rounded-2xl border p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">
          <TermLabel term="percentile">同龄人群对标</TermLabel>
        </h2>
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
          {benchmark.age_group} 岁 · {benchmark.cohort_size} 人样本
        </span>
      </div>

      <div className="space-y-4">
        {METRIC_LABELS.map(({ key, label, term, unit }) => (
          <PercentileBar
            key={key}
            metric={benchmark[key]}
            label={label}
            term={term}
            unit={unit}
          />
        ))}
      </div>

      <p className="text-xs text-gray-400 text-center">
        百分位基于平台内 {benchmark.age_group} 岁年龄组 {benchmark.cohort_size} 个已完成分析计算，
        数值越高表示衰老状态越好。
      </p>
    </div>
  );
}
