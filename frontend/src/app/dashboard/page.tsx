"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi, sampleApi, ApiError } from "@/lib/api";
import type { User, Sample } from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      try {
        const u = await authApi.me();
        if (!u.consent_given_at) {
          router.push("/consent");
          return;
        }
        setUser(u);
        const s = await sampleApi.list();
        setSamples(s);
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          router.push("/login");
        } else {
          setUser(null);
          setSamples([]);
        }
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [router]);

  const handleLogout = () => {
    authApi.logout();
    router.push("/login");
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center">加载中...</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-brand-700">基因抗衰老分析平台</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">{user?.email}</span>
          <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-700">
            退出
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto py-10 px-4 space-y-8">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-800">我的分析记录</h2>
          <Link
            href="/upload"
            className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm transition"
          >
            上传新数据
          </Link>
        </div>

        {samples.length === 0 ? (
          <div className="bg-white rounded-2xl border-2 border-dashed border-gray-200 p-12 text-center space-y-3">
            <p className="text-gray-500">暂无分析记录</p>
            <Link href="/upload" className="text-brand-600 hover:underline text-sm">
              上传您的第一份 DNA 甲基化数据 →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {samples.map((sample) => (
              <div key={sample.id} className="bg-white rounded-xl border p-5 flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-800">
                    {sample.array_type} 芯片数据
                  </p>
                  <p className="text-sm text-gray-500">
                    上传于 {new Date(sample.uploaded_at).toLocaleDateString("zh-CN")}
                    {sample.chronological_age && ` · ${sample.chronological_age} 岁`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
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
