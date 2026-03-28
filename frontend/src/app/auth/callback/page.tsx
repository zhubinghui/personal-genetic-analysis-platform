"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import Link from "next/link";

export default function OAuthCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    const err = searchParams.get("error");

    if (err) {
      setError("第三方登录失败，请重试");
      return;
    }

    if (token) {
      // 存储 JWT Token
      Cookies.set("access_token", token, {
        expires: 1,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
      });
      // 跳转到我的分析
      router.push("/dashboard");
    } else {
      setError("登录回调参数缺失");
    }
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-4">
          <div className="text-5xl">❌</div>
          <p className="text-red-500 font-medium">{error}</p>
          <Link href="/login" className="text-brand-600 hover:underline text-sm">
            返回登录
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center space-y-4">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-gray-600">登录中，正在跳转...</p>
      </div>
    </div>
  );
}
