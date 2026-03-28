"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Cookies from "js-cookie";

export default function Home() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = Cookies.get("access_token");
    if (token) {
      router.replace("/dashboard");
    } else {
      setChecking(false);
    }
  }, [router]);

  if (checking) return null;

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 bg-gradient-to-br from-brand-50 to-white">
      <div className="max-w-2xl text-center space-y-6">
        <h1 className="text-4xl font-bold text-brand-700">
          基因抗衰老分析平台
        </h1>
        <p className="text-lg text-gray-600">
          上传血液 DNA 甲基化数据，获取您的生物学年龄评估与个性化抗衰老建议。
        </p>
        <p className="text-sm text-gray-500">
          使用 DunedinPACE、Horvath Clock、GrimAge、PhenoAge 等先进模型
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/login"
            className="px-6 py-3 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition"
          >
            登录
          </Link>
          <Link
            href="/register"
            className="px-6 py-3 border border-brand-600 text-brand-600 rounded-lg hover:bg-brand-50 transition"
          >
            注册
          </Link>
        </div>
        <p className="text-xs text-gray-400 mt-8">
          本平台仅提供健康管理参考，不构成医疗诊断建议。所有数据使用 AES-256 加密保护。
        </p>
      </div>
    </main>
  );
}
