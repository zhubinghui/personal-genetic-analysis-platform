"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Dna, Mail } from "lucide-react";
import { authApi, ApiError } from "@/lib/api";
import SocialLoginButtons from "@/components/auth/SocialLoginButtons";

function getPasswordStrength(pw: string): { level: number; label: string; color: string } {
  if (pw.length === 0) return { level: 0, label: "", color: "bg-gray-200" };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;

  if (score <= 1) return { level: 1, label: "弱", color: "bg-red-500" };
  if (score <= 2) return { level: 2, label: "较弱", color: "bg-orange-500" };
  if (score <= 3) return { level: 3, label: "中等", color: "bg-yellow-500" };
  if (score <= 4) return { level: 4, label: "强", color: "bg-green-500" };
  return { level: 5, label: "非常强", color: "bg-brand-600" };
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [emailTouched, setEmailTouched] = useState(false);

  const pwStrength = useMemo(() => getPasswordStrength(password), [password]);
  const emailValid = !emailTouched || email.length === 0 || isValidEmail(email);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!isValidEmail(email)) {
      setError("请输入有效的邮箱地址");
      return;
    }
    if (password.length < 8) {
      setError("密码至少 8 位");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.register(email, password, phone || undefined);
      if (!res.code_sent) {
        setError(`注册成功，但验证码发送失败：${res.code_error ?? "未知错误"}。请稍后在登录页重新发送。`);
      }
      setRegistered(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "注册失败");
    } finally {
      setLoading(false);
    }
  };

  if (registered) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
        <div className="w-full max-w-sm text-center space-y-4">
          <Mail className="w-12 h-12 text-brand-600" />
          <h1 className="text-xl font-bold text-gray-800">注册成功！请验证邮箱</h1>
          <p className="text-sm text-gray-500 leading-relaxed">
            验证码已发送到 <strong>{email}</strong>
            {phone && <> 和手机 <strong>{phone}</strong></>}。<br />
            请输入验证码完成注册。
          </p>
          <Link
            href={`/verify-email?email=${encodeURIComponent(email)}${phone ? `&phone=${encodeURIComponent(phone)}` : ""}`}
            className="inline-block px-6 py-2.5 bg-brand-600 text-white rounded-xl font-medium hover:bg-brand-700 transition"
          >
            输入验证码
          </Link>
          <p className="text-xs text-gray-400">
            没有收到？
            <button
              onClick={async () => {
                try { await authApi.sendCode("email", email); alert("验证码已重新发送"); } catch (e) { alert(e instanceof ApiError ? e.message : "发送失败，请稍后重试"); }
              }}
              className="text-brand-600 hover:underline"
            >
              重新发送
            </button>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* 左侧品牌区域（复用 Login 风格） */}
      <div className="hidden lg:flex lg:w-1/2 gradient-brand flex-col justify-center px-16 relative overflow-hidden">
        <div className="relative z-10 max-w-lg">
          <Dna className="w-12 h-12 text-brand-600 mb-6" />
          <h1 className="text-3xl font-bold text-gray-800 mb-4">开始您的衰老分析之旅</h1>
          <p className="text-lg text-gray-600 leading-relaxed">
            创建账号后，您可以上传 DNA 甲基化数据，获取四大衰老时钟评估、19 维度系统分析和个性化的循证抗衰老建议。
          </p>
          <div className="mt-8 bg-white/60 backdrop-blur rounded-xl p-4 space-y-2">
            <p className="text-sm font-medium text-gray-800">注册即表示您同意：</p>
            <ul className="text-xs text-gray-600 space-y-1">
              <li>- 所有数据使用 AES-256-GCM 加密存储</li>
              <li>- 分析结果仅供健康管理参考</li>
              <li>- 您可随时删除数据（GDPR 合规）</li>
            </ul>
          </div>
        </div>
        <div className="absolute -right-20 -top-20 w-80 h-80 bg-brand-200/30 rounded-full" />
        <div className="absolute -left-10 -bottom-10 w-60 h-60 bg-brand-300/20 rounded-full" />
      </div>

      {/* 右侧注册表单 */}
      <div className="flex-1 flex items-center justify-center px-6 bg-white">
        <div className="w-full max-w-sm">
          <div className="lg:hidden text-center mb-8">
            <Dna className="w-10 h-10 text-brand-600" />
            <h1 className="text-xl font-bold text-gray-800 mt-2">基因抗衰老分析平台</h1>
          </div>

          <h2 className="text-2xl font-bold text-gray-800 mb-1">创建账号</h2>
          <p className="text-sm text-gray-500 mb-8">免费注册，开始您的个性化衰老分析</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">邮箱</label>
              <input
                type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => setEmailTouched(true)}
                placeholder="your@email.com"
                className={`w-full border rounded-xl px-4 py-3 text-sm bg-gray-50
                  focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition
                  ${!emailValid ? "border-red-300 bg-red-50" : "border-gray-200"}`}
              />
              {!emailValid && (
                <p className="text-xs text-red-500">请输入有效的邮箱格式</p>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">
                手机号 <span className="text-gray-400 font-normal">（选填，可用于短信验证）</span>
              </label>
              <input
                type="tel" value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="13800138000"
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm bg-gray-50
                           focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">密码</label>
              <input
                type="password" required minLength={8}
                value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="至少 8 位，包含大小写和数字更安全"
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm bg-gray-50
                           focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition"
              />
              {/* 密码强度指示条 */}
              {password.length > 0 && (
                <div className="space-y-1">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
                          i <= pwStrength.level ? pwStrength.color : "bg-gray-200"
                        }`}
                      />
                    ))}
                  </div>
                  <p className={`text-xs ${
                    pwStrength.level <= 2 ? "text-red-500" : pwStrength.level <= 3 ? "text-yellow-600" : "text-green-600"
                  }`}>
                    密码强度：{pwStrength.label}
                  </p>
                </div>
              )}
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-sm text-red-600">
                {error}
              </div>
            )}

            <button
              type="submit" disabled={loading || !isValidEmail(email) || password.length < 8}
              className="w-full py-3 bg-brand-600 text-white rounded-xl font-medium
                         hover:bg-brand-700 disabled:opacity-50 transition shadow-sm shadow-brand-200"
            >
              {loading ? "注册中..." : "创建账号"}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-6">
            已有账号？{" "}
            <Link href="/login" className="text-brand-600 hover:underline font-medium">返回登录</Link>
          </p>

          <div className="mt-6">
            <SocialLoginButtons />
          </div>
        </div>
      </div>
    </div>
  );
}
