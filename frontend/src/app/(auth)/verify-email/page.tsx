"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { authApi, ApiError } from "@/lib/api";

export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("验证链接无效，缺少 token 参数");
      return;
    }
    authApi.verifyEmail(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.message);
      })
      .catch((e) => {
        setStatus("error");
        setMessage(e instanceof ApiError ? e.message : "验证失败，请重试");
      });
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
      <div className="w-full max-w-sm text-center space-y-4">
        <div className="text-5xl">
          {status === "loading" ? "⏳" : status === "success" ? "✅" : "❌"}
        </div>
        <h1 className="text-xl font-bold text-gray-800">
          {status === "loading" ? "验证中..." : status === "success" ? "邮箱验证成功" : "验证失败"}
        </h1>
        <p className="text-sm text-gray-500">{message}</p>

        {status === "success" && (
          <Link
            href="/login"
            className="inline-block px-6 py-2.5 bg-brand-600 text-white rounded-xl font-medium hover:bg-brand-700 transition"
          >
            前往登录
          </Link>
        )}

        {status === "error" && (
          <div className="space-y-3">
            <Link href="/login" className="text-brand-600 hover:underline text-sm block">
              返回登录
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
