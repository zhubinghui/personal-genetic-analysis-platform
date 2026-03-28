"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine, ResponsiveContainer } from "recharts";
import type { DunedinPaceDimensions } from "@/types";
import { TermLabel } from "@/components/ui/InfoTip";

interface Props {
  dimensions: DunedinPaceDimensions;
}

const METRIC_LABELS: Record<string, string> = {
  blood_pressure: "血压", cholesterol: "总胆固醇", triglycerides: "甘油三酯",
  apoB: "载脂蛋白B", leptin: "瘦素",
  hba1c: "HbA1c", bmi: "BMI", waist_hip_ratio: "腰臀比",
  bun: "血尿素氮", creatinine_clearance: "肌酐清除率",
  alp: "碱性磷酸酶",
  fev1: "FEV1", fev1_fvc: "FEV1/FVC",
  crp: "CRP", wbc: "白细胞",
  attachment_loss: "牙周附着丧失",
  wechsler_score: "韦氏认知",
  balance: "平衡", sensorimotor: "感觉运动", grip_strength: "握力",
};

function getColor(score: number): string {
  if (score < 0.9) return "#22c55e";
  if (score < 1.1) return "#eab308";
  if (score < 1.3) return "#f97316";
  return "#ef4444";
}

export default function AgingDimensionBars({ dimensions }: Props) {
  const data: { name: string; score: number; fill: string }[] = [];

  Object.entries(dimensions).forEach(([, metrics]) => {
    Object.entries(metrics).forEach(([metric, score]) => {
      if (score !== null) {
        data.push({
          name: METRIC_LABELS[metric] ?? metric,
          score: Math.round((score as number) * 1000) / 1000,
          fill: getColor(score as number),
        });
      }
    });
  });

  data.sort((a, b) => b.score - a.score);

  const allNull = data.length === 0;

  return (
    <div className="card p-6">
      <h3 className="font-semibold text-gray-800 mb-1">
        <TermLabel term="dunedinpace">19 项生理维度评分</TermLabel>
      </h3>
      <p className="text-xs text-gray-400 mb-4">
        基于 <TermLabel term="dna_methylation">DunedinPACE</TermLabel> 模型探针加权贡献推断，仅供参考，不代表实测生化值
      </p>

      {allNull ? (
        <div className="flex flex-col items-center justify-center h-40 text-center text-gray-400 space-y-2">
          <p className="text-sm">当前样本的分项维度数据不可用</p>
          <p className="text-xs">DunedinPACE 综合评分已计算完成，请参考雷达图及总体建议</p>
        </div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={420}>
            <BarChart data={data} layout="vertical" margin={{ left: 80, right: 30 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" domain={[0.7, 1.4]} tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={80} />
              <ReferenceLine x={1.0} stroke="#6b7280" strokeDasharray="4 4" label={{ value: "均值", fontSize: 9, fill: "#6b7280" }} />
              <Tooltip formatter={(v: number) => [v.toFixed(3), "评分"]} />
              <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                {data.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-x-4 gap-y-1 justify-center mt-3 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-500 inline-block" /> 减缓（&lt;0.9）</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-400 inline-block" /> 正常（0.9-1.1）</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-orange-400 inline-block" /> 偏高（1.1-1.3）</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> 高风险（&gt;1.3）</span>
          </div>
        </>
      )}
    </div>
  );
}
