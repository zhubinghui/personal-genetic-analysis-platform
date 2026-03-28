"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";
import type { User } from "@/types";

const NAV_ITEMS = [
  { href: "/dashboard", label: "控制台", icon: "📊" },
  { href: "/trends", label: "历史对比", icon: "📈" },
  { href: "/upload", label: "上传数据", icon: "📤" },
];

const ADMIN_ITEMS = [
  { href: "/admin/knowledge", label: "知识库", icon: "📚" },
  { href: "/admin/users", label: "用户管理", icon: "👥" },
  { href: "/admin/settings", label: "设置", icon: "⚙️" },
];

export default function Navbar() {
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    authApi.me().then(setUser).catch(() => {});
    // 读取本地存储的主题偏好
    const saved = localStorage.getItem("theme");
    if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
      setDarkMode(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  const toggleDark = () => {
    setDarkMode(!darkMode);
    if (!darkMode) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  };

  const handleLogout = () => {
    authApi.logout();
    window.location.href = "/login";
  };

  if (!user) return null;

  return (
    <header className="bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 px-6 py-3 shadow-sm sticky top-0 z-40">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* 左侧：Logo + 导航 */}
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="flex items-center gap-2">
            <span className="text-xl">🧬</span>
            <span className="font-bold text-brand-700 dark:text-brand-400 hidden sm:inline">
              基因抗衰老
            </span>
          </Link>

          <nav className="flex gap-1">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition ${
                  pathname === item.href || pathname.startsWith(item.href + "/")
                    ? "bg-brand-50 text-brand-700 font-medium dark:bg-brand-900/30 dark:text-brand-400"
                    : "text-gray-500 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800"
                }`}
              >
                <span className="text-sm">{item.icon}</span>
                <span className="hidden md:inline">{item.label}</span>
              </Link>
            ))}

            {/* 管理员菜单 */}
            {user.is_admin && (
              <>
                <span className="w-px h-6 bg-gray-200 dark:bg-gray-700 mx-1 self-center" />
                {ADMIN_ITEMS.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition ${
                      pathname.startsWith(item.href)
                        ? "bg-amber-50 text-amber-700 font-medium dark:bg-amber-900/30 dark:text-amber-400"
                        : "text-gray-500 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800"
                    }`}
                  >
                    <span className="text-sm">{item.icon}</span>
                    <span className="hidden md:inline">{item.label}</span>
                  </Link>
                ))}
              </>
            )}
          </nav>
        </div>

        {/* 右侧：主题切换 + 用户信息 */}
        <div className="flex items-center gap-3">
          <button
            onClick={toggleDark}
            className="p-2 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
            title={darkMode ? "切换到浅色模式" : "切换到深色模式"}
          >
            {darkMode ? "☀️" : "🌙"}
          </button>

          <span className="text-sm text-gray-500 dark:text-gray-400 hidden sm:inline">
            {user.email}
          </span>

          {user.is_admin && (
            <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium dark:bg-amber-900/40 dark:text-amber-400">
              管理员
            </span>
          )}

          <button
            onClick={handleLogout}
            className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
          >
            退出
          </button>
        </div>
      </div>
    </header>
  );
}
