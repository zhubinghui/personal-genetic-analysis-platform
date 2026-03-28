import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center space-y-4 px-6">
        <div className="text-6xl">🧬</div>
        <h1 className="text-5xl font-bold text-gray-200">404</h1>
        <p className="text-lg text-gray-600 font-medium">页面未找到</p>
        <p className="text-sm text-gray-400 max-w-sm mx-auto">
          您访问的页面不存在或已被移除。请检查 URL 是否正确。
        </p>
        <div className="flex justify-center gap-3 pt-2">
          <Link
            href="/dashboard"
            className="px-4 py-2 bg-brand-600 text-white rounded-xl text-sm hover:bg-brand-700 transition shadow-sm"
          >
            返回控制台
          </Link>
          <Link
            href="/login"
            className="px-4 py-2 border border-gray-200 text-gray-600 rounded-xl text-sm hover:bg-gray-50 transition"
          >
            重新登录
          </Link>
        </div>
      </div>
    </div>
  );
}
