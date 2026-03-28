"use client";

import { useEffect, useState, useCallback } from "react";
import { adminUserApi, ApiError } from "@/lib/api";
import type { AdminUser } from "@/types";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminUserApi.list();
      setUsers(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleToggleRole = async (user: AdminUser) => {
    setActionLoading(user.id);
    try {
      const updated = await adminUserApi.setRole(user.id, !user.is_admin);
      setUsers((prev) => prev.map((u) => (u.id === user.id ? updated : u)));
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "操作失败");
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleStatus = async (user: AdminUser) => {
    const action = user.is_active ? "禁用" : "启用";
    if (!confirm(`确定要${action}用户 ${user.email}？`)) return;
    setActionLoading(user.id);
    try {
      const updated = await adminUserApi.setStatus(user.id, !user.is_active);
      setUsers((prev) => prev.map((u) => (u.id === user.id ? updated : u)));
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "操作失败");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-10 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800">用户管理</h1>
          <p className="text-sm text-gray-500 mt-1">共 {total} 位用户</p>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">加载中...</div>
      ) : error ? (
        <div className="text-center py-12 text-red-500">{error}</div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full data-table">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="pl-5">邮箱</th>
                <th>角色</th>
                <th>状态</th>
                <th>注册时间</th>
                <th className="pr-5 text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="pl-5">
                    <span className="font-medium text-gray-800">{user.email}</span>
                  </td>
                  <td>
                    {user.is_admin ? (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs font-medium">
                        管理员
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">普通用户</span>
                    )}
                  </td>
                  <td>
                    {user.is_active ? (
                      <span className="flex items-center gap-1 text-xs text-green-600">
                        <span className="w-2 h-2 bg-green-500 rounded-full" />
                        正常
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-red-500">
                        <span className="w-2 h-2 bg-red-500 rounded-full" />
                        已禁用
                      </span>
                    )}
                  </td>
                  <td className="text-xs text-gray-500">
                    {new Date(user.created_at).toLocaleDateString("zh-CN")}
                  </td>
                  <td className="pr-5">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => handleToggleRole(user)}
                        disabled={actionLoading === user.id}
                        className="text-xs px-2.5 py-1 border border-gray-200 rounded-lg
                                   text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition"
                      >
                        {user.is_admin ? "取消管理员" : "设为管理员"}
                      </button>
                      <button
                        onClick={() => handleToggleStatus(user)}
                        disabled={actionLoading === user.id}
                        className={`text-xs px-2.5 py-1 rounded-lg border disabled:opacity-50 transition ${
                          user.is_active
                            ? "border-red-200 text-red-600 hover:bg-red-50"
                            : "border-green-200 text-green-600 hover:bg-green-50"
                        }`}
                      >
                        {user.is_active ? "禁用" : "启用"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
