"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";
import type { User } from "@/types";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authApi.me()
      .then((u) => {
        // 前端只做展示；真正的权限校验在后端
        setUser(u);
      })
      .catch(() => router.push("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        加载中...
      </div>
    );
  }

  const navItems = [
    { href: "/admin/knowledge", label: "知识库文献" },
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* 顶部导航 */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/admin/knowledge" className="text-lg font-semibold text-brand-700">
            管理员控制台
          </Link>
          <nav className="flex gap-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`text-sm px-3 py-1.5 rounded-lg transition ${
                  pathname.startsWith(item.href)
                    ? "bg-brand-100 text-brand-700 font-medium"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">{user?.email}</span>
          <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-700">
            返回平台
          </Link>
        </div>
      </header>

      {/* 主内容 */}
      <main className="flex-1">{children}</main>
    </div>
  );
}
