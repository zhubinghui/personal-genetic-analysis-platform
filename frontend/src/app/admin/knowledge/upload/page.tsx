"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { knowledgeApi, ApiError } from "@/lib/api";

const ACCEPTED_TYPES = ".pdf,.docx,.txt,.md,.zip";
const MAX_SIZE_MB = 50;

export default function KnowledgeUploadPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<{ filename: string; status: string; title?: string; error?: string }[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    setFiles((prev) => [...prev, ...selected]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files ?? []);
    setFiles((prev) => [...prev, ...dropped]);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    setResults(null);

    try {
      const res = await knowledgeApi.uploadBatch(files);
      setResults(res.files);
      if (res.success === res.total) {
        setTimeout(() => router.push("/admin/knowledge"), 2000);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "上传失败，请重试");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-10 px-4">
      <div className="flex items-center gap-3 mb-8">
        <Link href="/admin/knowledge" className="text-gray-400 hover:text-gray-600 text-sm">
          ← 返回知识库
        </Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-semibold text-gray-800">批量上传文献</h1>
      </div>

      <div className="space-y-6">
        {/* 拖拽上传区域 */}
        <div
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
            files.length > 0 ? "border-brand-400 bg-brand-50" : "border-gray-300 hover:border-gray-400"
          }`}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept={ACCEPTED_TYPES}
            className="hidden"
            onChange={handleFileChange}
            multiple
          />
          <div className="space-y-2">
            <p className="text-3xl text-gray-300">📎</p>
            <p className="text-gray-600 font-medium">拖拽文件到此处，或点击选择</p>
            <p className="text-sm text-gray-400">
              支持 PDF / DOCX / TXT + ZIP 压缩包（自动解压）· 单文件最大 {MAX_SIZE_MB} MB
            </p>
            <p className="text-xs text-gray-400">
              PDF 文件将自动提取标题、作者、关键词等元数据
            </p>
          </div>
        </div>

        {/* 已选文件列表 */}
        {files.length > 0 && (
          <div className="card p-4 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-700">已选择 {files.length} 个文件</h3>
              <button onClick={() => setFiles([])} className="text-xs text-red-500 hover:underline">
                清空
              </button>
            </div>
            {files.map((f, i) => (
              <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-2 text-sm">
                  <span>{f.name.endsWith(".zip") ? "📦" : f.name.endsWith(".pdf") ? "📄" : "📝"}</span>
                  <span className="text-gray-800 truncate max-w-xs">{f.name}</span>
                  <span className="text-xs text-gray-400">{(f.size / 1024 / 1024).toFixed(1)} MB</span>
                </div>
                <button onClick={() => removeFile(i)} className="text-xs text-gray-400 hover:text-red-500">
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        {/* 上传结果 */}
        {results && (
          <div className="card p-4 space-y-2">
            <h3 className="text-sm font-medium text-gray-700">
              上传结果：{results.filter((r) => r.status === "ok").length}/{results.length} 成功
            </h3>
            {results.map((r, i) => (
              <div key={i} className={`flex items-center gap-2 py-1 text-sm ${r.status === "ok" ? "text-green-600" : "text-red-500"}`}>
                <span>{r.status === "ok" ? "✓" : "✗"}</span>
                <span className="truncate">{r.filename}</span>
                {r.title && r.status === "ok" && <span className="text-xs text-gray-400">→ {r.title}</span>}
                {r.error && <span className="text-xs">({r.error})</span>}
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleUpload}
            disabled={uploading || files.length === 0}
            className="flex-1 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 font-medium transition"
          >
            {uploading ? `上传中（${files.length} 个文件）...` : `上传并向量化（${files.length} 个文件）`}
          </button>
          <Link
            href="/admin/knowledge"
            className="px-4 py-2.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 text-sm transition"
          >
            取消
          </Link>
        </div>
      </div>
    </div>
  );
}
