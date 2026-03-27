"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { knowledgeApi, ApiError } from "@/lib/api";

const ACCEPTED_TYPES = ".pdf,.docx,.txt,.md";
const MAX_SIZE_MB = 50;

export default function KnowledgeUploadPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [authors, setAuthors] = useState("");
  const [journal, setJournal] = useState("");
  const [publishedYear, setPublishedYear] = useState("");
  const [doi, setDoi] = useState("");
  const [tags, setTags] = useState("");

  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    if (f && !title) {
      // 用文件名作为默认标题
      setTitle(f.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " "));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0] ?? null;
    if (f) {
      setFile(f);
      if (!title) setTitle(f.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " "));
    }
  };

  const validate = (): string | null => {
    if (!file) return "请选择要上传的文件";
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!["pdf", "docx", "txt", "md"].includes(ext))
      return "不支持的文件类型，仅支持 PDF / DOCX / TXT";
    if (file.size > MAX_SIZE_MB * 1024 * 1024)
      return `文件大小不能超过 ${MAX_SIZE_MB} MB`;
    if (!title.trim()) return "请填写文献标题";
    if (publishedYear && (isNaN(Number(publishedYear)) || Number(publishedYear) < 1900))
      return "发表年份格式不正确";
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate();
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    setUploading(true);

    try {
      await knowledgeApi.upload(file!, {
        title: title.trim(),
        description: description.trim() || undefined,
        authors: authors.trim() || undefined,
        journal: journal.trim() || undefined,
        published_year: publishedYear ? Number(publishedYear) : undefined,
        doi: doi.trim() || undefined,
        tags: tags.trim() || undefined,
      });
      router.push("/admin/knowledge");
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
        <h1 className="text-xl font-semibold text-gray-800">上传文献</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 文件上传区域 */}
        <div
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
            file ? "border-brand-400 bg-brand-50" : "border-gray-300 hover:border-gray-400"
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
          />
          {file ? (
            <div className="space-y-1">
              <p className="text-2xl">
                {file.name.endsWith(".pdf") ? "📄" : file.name.endsWith(".docx") ? "📝" : "📃"}
              </p>
              <p className="font-medium text-gray-800">{file.name}</p>
              <p className="text-sm text-gray-500">
                {(file.size / 1024 / 1024).toFixed(2)} MB · 点击重新选择
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-3xl text-gray-300">📎</p>
              <p className="text-gray-600 font-medium">拖拽文件到此处，或点击选择</p>
              <p className="text-sm text-gray-400">支持 PDF / DOCX / TXT，最大 {MAX_SIZE_MB} MB</p>
            </div>
          )}
        </div>

        {/* 元数据表单 */}
        <div className="bg-white rounded-xl border p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700 border-b pb-2">文献信息</h2>

          <Field label="标题 *">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="输入文献标题"
              className={INPUT_CLS}
              required
            />
          </Field>

          <Field label="摘要 / 简介">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="可选，输入文献摘要或简短说明"
              rows={3}
              className={INPUT_CLS}
            />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="作者">
              <input
                type="text"
                value={authors}
                onChange={(e) => setAuthors(e.target.value)}
                placeholder="如：Zhang Y, Li M, ..."
                className={INPUT_CLS}
              />
            </Field>
            <Field label="期刊/来源">
              <input
                type="text"
                value={journal}
                onChange={(e) => setJournal(e.target.value)}
                placeholder="如：Nature Aging"
                className={INPUT_CLS}
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="发表年份">
              <input
                type="number"
                value={publishedYear}
                onChange={(e) => setPublishedYear(e.target.value)}
                placeholder="如：2024"
                min={1900}
                max={2100}
                className={INPUT_CLS}
              />
            </Field>
            <Field label="DOI">
              <input
                type="text"
                value={doi}
                onChange={(e) => setDoi(e.target.value)}
                placeholder="如：10.1038/s43587-024-..."
                className={INPUT_CLS}
              />
            </Field>
          </div>

          <Field label="标签（逗号分隔）">
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="如：表观遗传, 抗衰老, DunedinPACE"
              className={INPUT_CLS}
            />
          </Field>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={uploading}
            className="flex-1 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 font-medium transition"
          >
            {uploading ? "上传中，请稍候..." : "上传并开始向量化"}
          </button>
          <Link
            href="/admin/knowledge"
            className="px-4 py-2.5 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 text-sm transition"
          >
            取消
          </Link>
        </div>

        <p className="text-xs text-gray-400 text-center">
          上传后系统将自动解析文档并生成本地嵌入向量，大型 PDF 可能需要几分钟。
        </p>
      </form>
    </div>
  );
}

const INPUT_CLS =
  "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-gray-600">{label}</label>
      {children}
    </div>
  );
}
