"use client";

import { useState, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { authApi, ApiError } from "@/lib/api";

function getPasswordStrength(pw: string) {
  if (!pw) return { level: 0, label: "", color: "bg-gray-200" };
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (/[A-Z]/.test(pw)) s++;
  if (/[0-9]/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  if (s <= 1) return { level: 1, label: "弱", color: "bg-red-500" };
  if (s <= 2) return { level: 2, label: "较弱", color: "bg-orange-500" };
  if (s <= 3) return { level: 3, label: "中等", color: "bg-yellow-500" };
  if (s <= 4) return { level: 4, label: "强", color: "bg-green-500" };
  return { level: 5, label: "非常强", color: "bg-brand-600" };
}

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const strength = useMemo(() => getPasswordStrength(password), [password]);

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-3">
          <p className="text-red-500">重置链接无效</p>
          <Link href="/forgot-password" className="text-brand-600 hover:underline text-sm">
            重新申请重置
          </Link>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
        <div className="w-full max-w-sm text-center space-y-4">
          <div className="text-5xl">✅</div>
          <h1 className="text-xl font-bold text-gray-800">密码重置成功</h1>
          <p className="text-sm text-gray-500">您的密码已更新，请使用新密码登录</p>
          <Link
            href="/login"
            className="inline-block px-6 py-2.5 bg-brand-600 text-white rounded-xl font-medium hover:bg-brand-700 transition"
          >
            前往登录
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("两次输入的密码不一致");
      return;
    }
    if (password.length < 8) {
      setError("密码至少 8 位");
      return;
    }
    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "重置失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="text-4xl">🔐</span>
          <h1 className="text-xl font-bold text-gray-800 mt-3">设置新密码</h1>
          <p className="text-sm text-gray-500 mt-1">请输入您的新密码</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">新密码</label>
            <input
              type="password" required minLength={8}
              value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 8 位"
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm bg-gray-50
                         focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition"
            />
            {password && (
              <div className="space-y-1">
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className={`h-1.5 flex-1 rounded-full transition-all ${i <= strength.level ? strength.color : "bg-gray-200"}`} />
                  ))}
                </div>
                <p className={`text-xs ${strength.level <= 2 ? "text-red-500" : strength.level <= 3 ? "text-yellow-600" : "text-green-600"}`}>
                  密码强度：{strength.label}
                </p>
              </div>
            )}
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">确认新密码</label>
            <input
              type="password" required minLength={8}
              value={confirm} onChange={(e) => setConfirm(e.target.value)}
              placeholder="再次输入新密码"
              className={`w-full border rounded-xl px-4 py-3 text-sm bg-gray-50
                         focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition
                         ${confirm && confirm !== password ? "border-red-300" : "border-gray-200"}`}
            />
            {confirm && confirm !== password && (
              <p className="text-xs text-red-500">两次密码不一致</p>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-sm text-red-600">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || password.length < 8 || password !== confirm}
            className="w-full py-3 bg-brand-600 text-white rounded-xl font-medium
                       hover:bg-brand-700 disabled:opacity-50 transition shadow-sm"
          >
            {loading ? "重置中..." : "重置密码"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          <Link href="/login" className="text-brand-600 hover:underline">← 返回登录</Link>
        </p>
      </div>
    </div>
  );
}
