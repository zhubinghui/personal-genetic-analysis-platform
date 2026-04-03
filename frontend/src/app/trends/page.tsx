"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from "recharts";
import ChartErrorBoundary from "@/components/ChartErrorBoundary";
import { trendApi, ApiError } from "@/lib/api";
import type { TrendResponse, TrendPoint } from "@/types";

const CLOCK_COLORS = {
  horvath: "#3b82f6",
  grimage: "#ef4444",
  phenoage: "#f59e0b",
  dunedinpace: "#10b981",
};

const SYSTEM_LABELS: Record<string, string> = {
  cardiovascular: "心血管",
  metabolic: "代谢",
  renal: "肾脏",
  hepatic: "肝脏",
  pulmonary: "肺功能",
  immune: "免疫",
  periodontal: "牙周",
  cognitive: "认知",
  physical: "体能",
};

export default function TrendsPage() {
  const router = useRouter();
  const [data, setData] = useState<TrendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    trendApi.get()
      .then(setData)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) router.push("/login");
        else setError(e instanceof ApiError ? e.message : "加载失败");
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  const points = data?.points ?? [];

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="text-brand-600 hover:underline text-sm">
            ← 我的分析
          </Link>
          <h1 className="text-lg font-semibold text-gray-800">历史趋势对比</h1>
        </div>
        <span className="text-sm text-gray-400">共 {points.length} 次采样</span>
      </header>

      <main className="max-w-6xl mx-auto py-8 px-4 space-y-8">
        {points.length < 2 ? (
          <div className="bg-white rounded-2xl border-2 border-dashed border-gray-200 p-12 text-center space-y-3">
            <p className="text-3xl">📈</p>
            <p className="text-gray-600 font-medium">
              {points.length === 0 ? "暂无分析结果" : "需要至少 2 次采样才能显示趋势对比"}
            </p>
            <p className="text-sm text-gray-400">
              上传新的 DNA 甲基化数据后，即可在此查看衰老指标的变化趋势
            </p>
            <Link href="/upload" className="inline-block text-brand-600 hover:underline text-sm mt-2">
              上传新数据 →
            </Link>
          </div>
        ) : (
          <>
            {/* 衰老时钟趋势折线图 */}
            <ChartErrorBoundary fallbackHeight="350px">
              <div className="bg-white rounded-2xl border p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-4">衰老时钟评分趋势</h2>
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={_buildClockChartData(points)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="label" fontSize={12} />
                    <YAxis fontSize={12} label={{ value: "岁 / 速率", angle: -90, position: "insideLeft" }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="实际年龄" stroke="#6b7280" strokeDasharray="5 5" dot={false} />
                    <Line type="monotone" dataKey="Horvath" stroke={CLOCK_COLORS.horvath} strokeWidth={2} />
                    <Line type="monotone" dataKey="GrimAge" stroke={CLOCK_COLORS.grimage} strokeWidth={2} />
                    <Line type="monotone" dataKey="PhenoAge" stroke={CLOCK_COLORS.phenoage} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </ChartErrorBoundary>

            {/* DunedinPACE 趋势 */}
            <ChartErrorBoundary fallbackHeight="250px">
              <div className="bg-white rounded-2xl border p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-4">DunedinPACE 衰老速率趋势</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={_buildPaceChartData(points)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="label" fontSize={12} />
                    <YAxis domain={[0.6, 1.4]} fontSize={12} />
                    <Tooltip />
                    <Line type="monotone" dataKey="DunedinPACE" stroke={CLOCK_COLORS.dunedinpace} strokeWidth={2.5} />
                    <Line type="monotone" dataKey="基准线" stroke="#d1d5db" strokeDasharray="5 5" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
                <p className="text-xs text-gray-400 mt-2 text-center">基准线 1.0 = 人群平均衰老速率</p>
              </div>
            </ChartErrorBoundary>

            {/* 维度雷达叠加对比 */}
            <ChartErrorBoundary fallbackHeight="400px">
              <div className="bg-white rounded-2xl border p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-4">系统维度变化对比（雷达图）</h2>
                <ResponsiveContainer width="100%" height={400}>
                  <RadarChart data={_buildRadarData(points)}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="system" fontSize={12} />
                    <PolarRadiusAxis domain={[0, 2]} tickCount={5} fontSize={10} />
                    {points.slice(-3).map((p, i) => {
                      const colors = ["#3b82f6", "#10b981", "#f59e0b"];
                      const date = new Date(p.uploaded_at).toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
                      return (
                        <Radar
                          key={p.sample_id}
                          name={date}
                          dataKey={`v${i}`}
                          stroke={colors[i]}
                          fill={colors[i]}
                          fillOpacity={0.1}
                          strokeWidth={2}
                        />
                      );
                    })}
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
                <p className="text-xs text-gray-400 text-center">展示最近 3 次采样的 9 大系统评分叠加对比</p>
              </div>
            </ChartErrorBoundary>

            {/* 历史数据表格 */}
            <div className="bg-white rounded-2xl border p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">历史数据明细</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-gray-500">
                      <th className="py-2 pr-4">日期</th>
                      <th className="py-2 pr-4">年龄</th>
                      <th className="py-2 pr-4">Horvath</th>
                      <th className="py-2 pr-4">GrimAge</th>
                      <th className="py-2 pr-4">PhenoAge</th>
                      <th className="py-2 pr-4">DunedinPACE</th>
                      <th className="py-2">加速值</th>
                    </tr>
                  </thead>
                  <tbody>
                    {points.map((p) => (
                      <tr key={p.sample_id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="py-2 pr-4">{new Date(p.uploaded_at).toLocaleDateString("zh-CN")}</td>
                        <td className="py-2 pr-4">{p.chronological_age ?? "—"}</td>
                        <td className="py-2 pr-4">{p.horvath_age?.toFixed(1) ?? "—"}</td>
                        <td className="py-2 pr-4">{p.grimage_age?.toFixed(1) ?? "—"}</td>
                        <td className="py-2 pr-4">{p.phenoage_age?.toFixed(1) ?? "—"}</td>
                        <td className="py-2 pr-4 font-medium">
                          <span className={p.dunedinpace && p.dunedinpace > 1.1 ? "text-red-500" : "text-green-600"}>
                            {p.dunedinpace?.toFixed(3) ?? "—"}
                          </span>
                        </td>
                        <td className="py-2">
                          {p.biological_age_acceleration != null
                            ? `${p.biological_age_acceleration > 0 ? "+" : ""}${p.biological_age_acceleration.toFixed(1)}`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

// ── 数据转换函数 ──────────────────────────────────────────

function _buildClockChartData(points: TrendPoint[]) {
  return points.map((p) => ({
    label: new Date(p.uploaded_at).toLocaleDateString("zh-CN", { month: "short", day: "numeric" }),
    "实际年龄": p.chronological_age,
    Horvath: p.horvath_age ? +p.horvath_age.toFixed(1) : null,
    GrimAge: p.grimage_age ? +p.grimage_age.toFixed(1) : null,
    PhenoAge: p.phenoage_age ? +p.phenoage_age.toFixed(1) : null,
  }));
}

function _buildPaceChartData(points: TrendPoint[]) {
  return points.map((p) => ({
    label: new Date(p.uploaded_at).toLocaleDateString("zh-CN", { month: "short", day: "numeric" }),
    DunedinPACE: p.dunedinpace ? +p.dunedinpace.toFixed(3) : null,
    "基准线": 1.0,
  }));
}

function _buildRadarData(points: TrendPoint[]) {
  const recent = points.slice(-3);
  const systems = Object.keys(SYSTEM_LABELS);
  return systems.map((sys) => {
    const entry: Record<string, string | number | null> = { system: SYSTEM_LABELS[sys] };
    recent.forEach((p, i) => {
      entry[`v${i}`] = p.dimension_summary[sys] ?? null;
    });
    return entry;
  });
}
