"use client";

import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, ResponsiveContainer, Tooltip,
} from "recharts";
import type { DunedinPaceDimensions } from "@/types";

interface Props {
  dimensions: DunedinPaceDimensions;
  paceScore: number;
}

const CATEGORY_LABELS: Record<string, string> = {
  cardiovascular: "心血管",
  metabolic: "代谢",
  renal: "肾脏",
  hepatic: "肝脏",
  pulmonary: "肺功能",
  immune: "免疫",
  periodontal: "牙周",
  cognitive: "认知",
  physical: "身体功能",
};

function categoryAverage(metrics: Record<string, number | null>): number {
  const vals = Object.values(metrics).filter((v) => v !== null) as number[];
  if (!vals.length) return 1.0;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function getPaceColor(score: number): string {
  if (score < 0.9) return "#22c55e";
  if (score < 1.1) return "#eab308";
  if (score < 1.3) return "#f97316";
  return "#ef4444";
}

export default function DunedinPaceRadar({ dimensions, paceScore }: Props) {
  const data = Object.entries(dimensions).map(([key, metrics]) => ({
    category: CATEGORY_LABELS[key] ?? key,
    score: Math.round(categoryAverage(metrics) * 100) / 100,
  }));

  // 判断是否所有维度均为默认值（全 null → 均为 1.0）
  const allDefault = data.every((d) => d.score === 1.0);

  const color = getPaceColor(paceScore);

  return (
    <div className="bg-white rounded-2xl border p-6">
      <div className="flex items-start justify-between mb-4">
        <h3 className="font-semibold text-gray-800">DunedinPACE 系统维度</h3>
        <div className="text-right">
          <p className="text-3xl font-bold" style={{ color }}>{paceScore.toFixed(3)}</p>
          <p className="text-xs text-gray-400">衰老速率（1.0 = 人群均值）</p>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="category" tick={{ fontSize: 11 }} />
          <PolarRadiusAxis domain={[0.7, 1.3]} tick={false} />
          <Radar
            name="系统评分" dataKey="score"
            stroke={color} fill={color} fillOpacity={0.35}
          />
          <Tooltip formatter={(v: number) => [v.toFixed(3), "系统评分"]} />
        </RadarChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-400 text-center mt-2">
        {allDefault
          ? "分项数据不可用，图形仅展示综合评分基准线；请参考下方总体建议"
          : "各系统维度为对应指标的相对衰老速率；1.0 为人群基准，颜色标注风险等级"}
      </p>
    </div>
  );
}
