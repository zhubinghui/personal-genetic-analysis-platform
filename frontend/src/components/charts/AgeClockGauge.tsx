"use client";

import {
  RadarChart, PolarGrid, PolarAngleAxis,
  Radar, Legend, ResponsiveContainer, Tooltip,
} from "recharts";

interface Props {
  horvathAge: number | null;
  grimAge: number | null;
  phenoAge: number | null;
  chronologicalAge: number | null;
}

export default function AgeClockGauge({ horvathAge, grimAge, phenoAge, chronologicalAge }: Props) {
  const chron = chronologicalAge ?? 40;

  const data = [
    { clock: "Horvath", 生物学年龄: horvathAge ?? 0, 实际年龄: chron },
    { clock: "GrimAge", 生物学年龄: grimAge ?? 0, 实际年龄: chron },
    { clock: "PhenoAge", 生物学年龄: phenoAge ?? 0, 实际年龄: chron },
  ].filter((d) => d["生物学年龄"] > 0);

  return (
    <div className="bg-white rounded-2xl border p-6">
      <h3 className="font-semibold text-gray-800 mb-4">衰老时钟对比</h3>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="clock" />
          <Radar name="生物学年龄" dataKey="生物学年龄" stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
          <Radar name="实际年龄" dataKey="实际年龄" stroke="#22c55e" fill="#22c55e" fillOpacity={0.2} />
          <Legend />
          <Tooltip />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
