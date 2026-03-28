"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi, ApiError } from "@/lib/api";
import SocialLoginButtons from "@/components/auth/SocialLoginButtons";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await authApi.login(email, password);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("UNVERIFIED");
      } else {
        setError(err instanceof ApiError ? err.message : "登录失败");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* 左侧品牌区域 */}
      <div className="hidden lg:flex lg:w-1/2 gradient-brand flex-col justify-center px-16 relative overflow-hidden">
        <div className="relative z-10 max-w-lg">
          <div className="text-5xl mb-6">🧬</div>
          <h1 className="text-3xl font-bold text-gray-800 mb-4">基因抗衰老分析平台</h1>
          <p className="text-lg text-gray-600 mb-8 leading-relaxed">
            上传血液 DNA 甲基化数据，获取个性化的生物学年龄评估与循证抗衰老建议。
          </p>
          <div className="space-y-3">
            {[
              { icon: "🔬", title: "4 大衰老时钟", desc: "Horvath、GrimAge、PhenoAge、DunedinPACE" },
              { icon: "📊", title: "19 维度深度分析", desc: "心血管、代谢、免疫等 9 大系统分项评估" },
              { icon: "📋", title: "循证干预建议", desc: "基于 PubMed 文献的个性化抗衰老方案" },
              { icon: "🔒", title: "隐私优先设计", desc: "AES-256 加密 + 假名化数据架构" },
            ].map((item) => (
              <div key={item.title} className="flex items-start gap-3 bg-white/60 backdrop-blur rounded-xl p-3">
                <span className="text-xl mt-0.5">{item.icon}</span>
                <div>
                  <p className="font-medium text-gray-800 text-sm">{item.title}</p>
                  <p className="text-xs text-gray-500">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="absolute -right-20 -top-20 w-80 h-80 bg-brand-200/30 rounded-full" />
        <div className="absolute -left-10 -bottom-10 w-60 h-60 bg-brand-300/20 rounded-full" />
      </div>

      {/* 右侧登录表单 */}
      <div className="flex-1 flex items-center justify-center px-6 bg-white">
        <div className="w-full max-w-sm">
          <div className="lg:hidden text-center mb-8">
            <span className="text-4xl">🧬</span>
            <h1 className="text-xl font-bold text-gray-800 mt-2">基因抗衰老分析平台</h1>
          </div>

          <h2 className="text-2xl font-bold text-gray-800 mb-1">欢迎回来</h2>
          <p className="text-sm text-gray-500 mb-8">登录您的账号继续使用平台</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">邮箱</label>
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm bg-gray-50
                           focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">密码</label>
              <input
                type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="输入密码"
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm bg-gray-50
                           focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition"
              />
            </div>

            {error === "UNVERIFIED" ? (
              <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm space-y-2">
                <p className="text-amber-700 font-medium">请先验证邮箱</p>
                <p className="text-amber-600 text-xs">注册时已发送验证邮件到您的邮箱，请查看收件箱（含垃圾邮件）。</p>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await authApi.sendCode("email", email);
                      setError("RESENT");
                    } catch {}
                  }}
                  className="text-xs text-brand-600 hover:underline"
                >
                  重新发送验证码
                </button>
              </div>
            ) : error === "RESENT" ? (
              <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-2.5 text-sm text-green-600">
                验证邮件已重新发送，请查看收件箱
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-sm text-red-600">
                {error}
              </div>
            ) : null}

            <button
              type="submit" disabled={loading}
              className="w-full py-3 bg-brand-600 text-white rounded-xl font-medium
                         hover:bg-brand-700 disabled:opacity-50 transition shadow-sm shadow-brand-200"
            >
              {loading ? "登录中..." : "登录"}
            </button>
          </form>

          <div className="flex items-center justify-between mt-6 text-sm text-gray-500">
            <Link href="/forgot-password" className="hover:text-brand-600 transition">
              忘记密码？
            </Link>
            <span>
              没有账号？{" "}
              <Link href="/register" className="text-brand-600 hover:underline font-medium">立即注册</Link>
            </span>
          </div>

          <div className="mt-6">
            <SocialLoginButtons />
          </div>
          <p className="text-center text-xs text-gray-400 mt-8">
            本平台仅提供健康管理参考，不构成医疗诊断建议。
          </p>
        </div>
      </div>
    </div>
  );
}
