"use client";

import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import Cookies from "js-cookie";
import { authApi, ApiError } from "@/lib/api";

export default function VerifyEmailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailParam = searchParams.get("email") ?? "";
  const phoneParam = searchParams.get("phone") ?? "";

  const [channel, setChannel] = useState<"email" | "sms">(phoneParam ? "sms" : "email");
  const [target] = useState(channel === "sms" ? phoneParam : emailParam);
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<"input" | "success" | "error">("input");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  const handleVerify = async () => {
    if (code.length !== 6) return;
    setLoading(true);
    try {
      const res = await authApi.verifyCode(channel, target, code);
      // 后端验证成功后返回 token，直接登录
      if (res.access_token) {
        Cookies.set("access_token", res.access_token, {
          expires: 1,
          sameSite: process.env.NODE_ENV === "production" ? "strict" : "lax",
        });
        router.push("/dashboard");
        return;
      }
      setStatus("success");
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "验证失败");
      setStatus("error");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      await authApi.sendCode(channel, target);
      setMessage("验证码已重新发送");
      setTimeout(() => setMessage(""), 3000);
    } catch {} finally {
      setResending(false);
    }
  };

  if (status === "success") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
        <div className="w-full max-w-sm text-center space-y-4">
          <div className="text-5xl">✅</div>
          <h1 className="text-xl font-bold text-gray-800">验证成功</h1>
          <p className="text-sm text-gray-500">您的账号已验证，现在可以登录了</p>
          <Link href="/login" className="inline-block px-6 py-2.5 bg-brand-600 text-white rounded-xl font-medium hover:bg-brand-700 transition">
            前往登录
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
      <div className="w-full max-w-sm text-center space-y-6">
        <div className="text-5xl">📩</div>
        <h1 className="text-xl font-bold text-gray-800">输入验证码</h1>
        <p className="text-sm text-gray-500">
          验证码已发送到{channel === "email" ? "邮箱" : "手机"} <strong>{target}</strong>
        </p>

        {/* 6位验证码输入 */}
        <input
          type="text"
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          placeholder="000000"
          className="w-full text-center text-3xl tracking-[12px] font-bold border border-gray-200
                     rounded-xl px-4 py-4 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
        />

        {(message || status === "error") && (
          <p className={`text-sm ${status === "error" ? "text-red-500" : "text-green-600"}`}>{message}</p>
        )}

        <button
          onClick={handleVerify}
          disabled={code.length !== 6 || loading}
          className="w-full py-3 bg-brand-600 text-white rounded-xl font-medium
                     hover:bg-brand-700 disabled:opacity-50 transition"
        >
          {loading ? "验证中..." : "验证"}
        </button>

        <p className="text-xs text-gray-400">
          没有收到？{" "}
          <button onClick={handleResend} disabled={resending} className="text-brand-600 hover:underline disabled:opacity-50">
            {resending ? "发送中..." : "重新发送"}
          </button>
        </p>

        <Link href="/login" className="text-sm text-gray-500 hover:text-brand-600 block">
          ← 返回登录
        </Link>
      </div>
    </div>
  );
}
