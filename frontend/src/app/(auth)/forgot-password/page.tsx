"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Smartphone, KeyRound } from "lucide-react";
import { authApi, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [channel, setChannel] = useState<"email" | "sms">("email");
  const [target, setTarget] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await authApi.forgotPassword(channel, target);
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "发送失败");
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
        <div className="w-full max-w-sm text-center space-y-4">
          <div className="flex justify-center">{channel === "email" ? <Mail className="w-12 h-12 text-brand-600" /> : <Smartphone className="w-12 h-12 text-brand-600" />}</div>
          <h1 className="text-xl font-bold text-gray-800">验证码已发送</h1>
          <p className="text-sm text-gray-500">
            重置验证码已发送到{channel === "email" ? "邮箱" : "手机"} <strong>{target}</strong>
          </p>
          <button
            onClick={() => router.push(`/reset-password?channel=${channel}&target=${encodeURIComponent(target)}`)}
            className="w-full py-3 bg-brand-600 text-white rounded-xl font-medium hover:bg-brand-700 transition"
          >
            输入验证码重置密码
          </button>
          <Link href="/login" className="text-sm text-gray-500 hover:text-brand-600 block">
            ← 返回登录
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <KeyRound className="w-10 h-10 text-brand-600" />
          <h1 className="text-xl font-bold text-gray-800 mt-3">忘记密码</h1>
          <p className="text-sm text-gray-500 mt-1">选择验证方式接收重置验证码</p>
        </div>

        {/* 通道切换 */}
        <div className="flex rounded-xl bg-gray-100 p-1 mb-6">
          {(["email", "sms"] as const).map((ch) => (
            <button
              key={ch}
              onClick={() => { setChannel(ch); setTarget(""); }}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
                channel === ch ? "bg-white text-brand-600 shadow-sm" : "text-gray-500"
              }`}
            >
              {ch === "email" ? "邮箱" : "手机"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <input
            type={channel === "email" ? "email" : "tel"}
            required
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder={channel === "email" ? "your@email.com" : "13800138000"}
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm bg-gray-50
                       focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
          />

          {error && <p className="text-sm text-red-500">{error}</p>}

          <button
            type="submit" disabled={loading || !target}
            className="w-full py-3 bg-brand-600 text-white rounded-xl font-medium hover:bg-brand-700 disabled:opacity-50 transition"
          >
            {loading ? "发送中..." : "发送重置验证码"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          <Link href="/login" className="text-brand-600 hover:underline">← 返回登录</Link>
        </p>
      </div>
    </div>
  );
}
