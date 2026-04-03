"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Upload, Trash2 } from "lucide-react";
import { authApi, sampleApi, ApiError } from "@/lib/api";
import { useTokenRefresh } from "@/lib/tokenRefresh";
import Navbar from "@/components/layout/Navbar";
import type { User, Sample } from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Token 自动刷新
  useTokenRefresh();

  useEffect(() => {
    const init = async () => {
      try {
        const [u, s] = await Promise.all([authApi.me(), sampleApi.list()]);
        if (!u.consent_given_at) {
          router.push("/consent");
          return;
        }
        setUser(u);
        setSamples(s);
      } catch {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [router]);

  const handleDeleteSample = async (sampleId: string) => {
    if (!confirm("确定要删除该采样数据及其所有分析结果吗？此操作不可撤销。")) return;
    setDeleting(sampleId);
    try {
      await sampleApi.delete(sampleId);
      setSamples((prev) => prev.filter((s) => s.id !== sampleId));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "删除失败");
    } finally {
      setDeleting(null);
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center">加载中...</div>;

  // 统计概览
  const completedSamples = samples.filter((s) => s.latest_job_status === "completed");
  const latestCompleted = completedSamples[0]; // 已按 uploaded_at DESC 排序

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-5xl mx-auto py-8 px-4 space-y-6">
        {/* 数据概览卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4 text-center">
            <p className="text-2xl metric-value text-brand-600">{samples.length}</p>
            <p className="text-xs text-gray-400 mt-1">总采样次数</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl metric-value text-green-600">{completedSamples.length}</p>
            <p className="text-xs text-gray-400 mt-1">已完成分析</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl metric-value text-gray-800">
              {latestCompleted?.chronological_age ?? "—"}<span className="text-sm font-normal text-gray-400"> 岁</span>
            </p>
            <p className="text-xs text-gray-400 mt-1">最新采样年龄</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl metric-value text-blue-600">
              {completedSamples.length > 0 ? "可用" : "—"}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              <Link href="/trends" className="text-brand-600 hover:underline">
                趋势报告 →
              </Link>
            </p>
          </div>
        </div>

        {/* 样本列表 */}
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-800">我的分析记录</h2>
          <Link
            href="/upload"
            className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm transition shadow-sm"
          >
            上传新数据
          </Link>
        </div>

        {samples.length === 0 ? (
          <div className="card border-2 border-dashed border-gray-200 p-12 text-center space-y-3">
            <Upload className="w-10 h-10 text-gray-300" />
            <p className="text-gray-500 font-medium">暂无分析记录</p>
            <Link href="/upload" className="text-brand-600 hover:underline text-sm">
              上传您的第一份 DNA 甲基化数据 →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {samples.map((sample) => (
              <div key={sample.id} className="card p-5 flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-800">
                    {sample.array_type} 芯片数据
                  </p>
                  <p className="text-sm text-gray-500">
                    上传于 {new Date(sample.uploaded_at).toLocaleDateString("zh-CN")}
                    {sample.chronological_age && ` · ${sample.chronological_age} 岁`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <JobStatusBadge jobStatus={sample.latest_job_status} />
                  {sample.latest_job_status === "completed" && sample.latest_job_id && (
                    <Link
                      href={`/results/${sample.latest_job_id}`}
                      className="px-3 py-1.5 bg-brand-600 text-white rounded-lg text-sm hover:bg-brand-700 transition"
                    >
                      查看结果
                    </Link>
                  )}
                  {sample.latest_job_status === "running" && sample.latest_job_id && (
                    <Link
                      href={`/results/${sample.latest_job_id}`}
                      className="px-3 py-1.5 border border-brand-600 text-brand-600 rounded-lg text-sm hover:bg-brand-50 transition"
                    >
                      查看进度
                    </Link>
                  )}
                  <button
                    onClick={() => handleDeleteSample(sample.id)}
                    disabled={deleting === sample.id}
                    className="px-2.5 py-1.5 text-xs text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition disabled:opacity-50"
                    title="删除此采样数据"
                  >
                    {deleting === sample.id ? "删除中..." : <Trash2 className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function JobStatusBadge({ jobStatus }: { jobStatus: string | null }) {
  if (!jobStatus) return null;
  const map: Record<string, { label: string; cls: string }> = {
    queued:    { label: "排队中", cls: "bg-gray-100 text-gray-600" },
    running:   { label: "分析中", cls: "bg-blue-100 text-blue-700" },
    completed: { label: "已完成", cls: "bg-green-100 text-green-700" },
    failed:    { label: "失败",   cls: "bg-red-100 text-red-700" },
  };
  const s = map[jobStatus] ?? { label: jobStatus, cls: "bg-gray-100 text-gray-700" };
  return (
    <span className={`px-3 py-1 rounded-full text-xs font-medium ${s.cls}`}>{s.label}</span>
  );
}
