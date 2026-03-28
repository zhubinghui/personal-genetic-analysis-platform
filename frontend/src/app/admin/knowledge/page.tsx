"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Cookies from "js-cookie";
import { knowledgeApi, ApiError } from "@/lib/api";
import type { KnowledgeDocument, DocumentStatus } from "@/types";

const STATUS_MAP: Record<DocumentStatus, { label: string; cls: string }> = {
  pending:    { label: "待处理", cls: "bg-gray-100 text-gray-600" },
  processing: { label: "向量化中", cls: "bg-blue-100 text-blue-700" },
  ready:      { label: "已就绪", cls: "bg-green-100 text-green-700" },
  failed:     { label: "失败",   cls: "bg-red-100 text-red-700" },
};

const FILE_TYPE_ICON: Record<string, string> = {
  pdf: "📄",
  docx: "📝",
  txt: "📃",
  md: "📃",
};

function formatBytes(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function KnowledgeListPage() {
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [reprocessing, setReprocessing] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Array<{
    document_title: string;
    chunk_text: string;
    page_number: number | null;
    score: number;
  }> | null>(null);
  const [searching, setSearching] = useState(false);
  const [stats, setStats] = useState<{ total: number; ready: number; processing: number; pending: number; failed: number; total_chunks: number } | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // 认证失败标记：阻止轮询继续刷 401
  const [authFailed, setAuthFailed] = useState(false);
  const [initialLoaded, setInitialLoaded] = useState(false);

  // silent=true 时不显示 loading 闪烁（后台静默刷新）
  const loadDocs = useCallback(async (p: number = 1, silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const skip = (p - 1) * pageSize;
      const res = await knowledgeApi.list({ skip, limit: pageSize });
      setDocs(res.items);
      setTotal(res.total);
      setAuthFailed(false);
      setInitialLoaded(true);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setAuthFailed(true);
        setError("登录已过期，请重新登录");
      } else if (!silent) {
        setError(e instanceof ApiError ? e.message : "加载失败");
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const s = await knowledgeApi.stats();
      setStats(s);
    } catch {}
  }, []);

  useEffect(() => {
    loadDocs(page);
    loadStats();
    // 轮询使用 silent 模式：后台静默刷新，不触发 loading 状态，不改变排序体验
    const timer = setInterval(() => {
      if (!authFailed) { loadDocs(page, true); loadStats(); }
    }, 10_000);
    return () => clearInterval(timer);
  }, [loadDocs, loadStats, authFailed, page]);

  const handleDelete = async (docId: string) => {
    if (!confirm("确定要删除该文献吗？此操作不可撤销。")) return;
    setDeleting(docId);
    try {
      await knowledgeApi.delete(docId);
      setDocs((prev) => prev.filter((d) => d.id !== docId));
      setTotal((t) => t - 1);
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "删除失败");
    } finally {
      setDeleting(null);
    }
  };

  const handleReprocess = async (docId: string) => {
    setReprocessing(docId);
    try {
      const updated = await knowledgeApi.reprocess(docId);
      setDocs((prev) => prev.map((d) => (d.id === docId ? updated : d)));
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "重新处理失败");
    } finally {
      setReprocessing(null);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setSearchResults(null);
    try {
      const res = await knowledgeApi.search(searchQuery.trim(), 8, 0.2);
      setSearchResults(res.results);
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "搜索失败");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-10 px-4 space-y-8">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800">知识库文献</h1>
          {stats && (
            <div className="flex items-center gap-3 mt-1.5 text-xs">
              <span className="text-gray-500">共 {stats.total} 篇</span>
              {stats.ready > 0 && (
                <span className="flex items-center gap-1 text-green-600">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                  {stats.ready} 篇已向量化
                </span>
              )}
              {stats.processing > 0 && (
                <span className="flex items-center gap-1 text-blue-600">
                  <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
                  {stats.processing} 篇处理中
                </span>
              )}
              {stats.pending > 0 && (
                <span className="text-amber-600">{stats.pending} 篇等待处理</span>
              )}
              {stats.failed > 0 && (
                <span className="text-red-500">{stats.failed} 篇失败</span>
              )}
              <span className="text-gray-400">{stats.total_chunks.toLocaleString()} 个向量切片</span>
            </div>
          )}
        </div>
        <Link
          href="/admin/knowledge/upload"
          className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm transition"
        >
          + 上传文献
        </Link>
      </div>

      {/* 语义搜索测试框 */}
      <div className="bg-white rounded-xl border p-5 space-y-3">
        <h2 className="text-sm font-medium text-gray-700">语义搜索测试</h2>
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="输入查询语句，按 Enter 或点击搜索..."
            className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            onClick={handleSearch}
            disabled={searching || !searchQuery.trim()}
            className="px-4 py-2 bg-brand-600 text-white rounded-lg text-sm hover:bg-brand-700 disabled:opacity-50 transition"
          >
            {searching ? "搜索中..." : "搜索"}
          </button>
        </div>

        {searchResults !== null && (
          <div className="space-y-2 pt-1">
            {searchResults.length === 0 ? (
              <p className="text-sm text-gray-400">未找到相关内容</p>
            ) : (
              searchResults.map((r, i) => (
                <div key={i} className="bg-gray-50 rounded-lg p-3 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-brand-700">{r.document_title}</span>
                    <span className="text-xs text-gray-400">
                      相关度 {(r.score * 100).toFixed(1)}%
                      {r.page_number && ` · 第 ${r.page_number} 页`}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 line-clamp-3">{r.chunk_text}</p>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* 文献列表 */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">加载中...</div>
      ) : error ? (
        <div className="text-center py-12 text-red-500">{error}</div>
      ) : docs.length === 0 ? (
        <div className="bg-white rounded-2xl border-2 border-dashed border-gray-200 p-12 text-center space-y-3">
          <p className="text-gray-500">暂无文献</p>
          <Link href="/admin/knowledge/upload" className="text-brand-600 hover:underline text-sm">
            上传第一篇文献 →
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {docs.map((doc) => {
            const s = STATUS_MAP[doc.status];
            return (
              <div key={doc.id} className="bg-white rounded-xl border p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg">{FILE_TYPE_ICON[doc.file_type] ?? "📄"}</span>
                      <h3 className="font-medium text-gray-800 truncate">{doc.title}</h3>
                      <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${s.cls}`}>
                        {s.label}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-500">
                      {doc.authors && <span>作者：{doc.authors}</span>}
                      {doc.journal && <span>期刊：{doc.journal}</span>}
                      {doc.published_year && <span>{doc.published_year} 年</span>}
                      {doc.doi && <span>DOI: {doc.doi}</span>}
                      <span>{doc.file_name} · {formatBytes(doc.file_size_bytes)}</span>
                      {doc.status === "ready" && (
                        <span className="text-green-600">{doc.chunk_count} 个切片</span>
                      )}
                    </div>

                    {doc.tags && doc.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {doc.tags.map((tag) => (
                          <span key={tag} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}

                    {doc.status === "failed" && doc.error_message && (
                      <p className="text-xs text-red-500 mt-1">{doc.error_message}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {doc.file_type === "pdf" && doc.status === "ready" && (
                      <a
                        href={`/api/v1/admin/knowledge/${doc.id}/preview?token=${Cookies.get("access_token") ?? ""}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs px-3 py-1.5 border border-brand-200 text-brand-600 rounded-lg hover:bg-brand-50 transition"
                      >
                        预览 PDF
                      </a>
                    )}
                    {(doc.status === "failed" || doc.status === "ready") && (
                      <button
                        onClick={() => handleReprocess(doc.id)}
                        disabled={reprocessing === doc.id}
                        className="text-xs px-3 py-1.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition"
                      >
                        {reprocessing === doc.id ? "处理中..." : "重新向量化"}
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(doc.id)}
                      disabled={deleting === doc.id}
                      className="text-xs px-3 py-1.5 border border-red-200 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50 transition"
                    >
                      {deleting === doc.id ? "删除中..." : "删除"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 分页 */}
      {!loading && !error && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-400">
            第 {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} 篇，共 {total} 篇
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-600
                         hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition"
            >
              上一页
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
              .reduce<(number | "...")[]>((acc, p, idx, arr) => {
                if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push("...");
                acc.push(p);
                return acc;
              }, [])
              .map((item, idx) =>
                item === "..." ? (
                  <span key={`e${idx}`} className="px-2 text-gray-400 text-sm">...</span>
                ) : (
                  <button
                    key={item}
                    onClick={() => setPage(item as number)}
                    className={`w-8 h-8 text-sm rounded-lg transition ${
                      page === item ? "bg-brand-600 text-white font-medium" : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    {item}
                  </button>
                )
              )}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-600
                         hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition"
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
