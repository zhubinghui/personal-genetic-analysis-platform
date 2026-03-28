import Cookies from "js-cookie";
import type {
  AdminUser,
  AdminUserList,
  AnalysisResult,
  JobStatus,
  KnowledgeDocument,
  KnowledgeDocumentList,
  ReportData,
  Sample,
  SampleUploadResponse,
  SearchResponse,
  TokenResponse,
  TrendResponse,
  User,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function apiFetch<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth = true, ...fetchOptions } = options;
  const headers: Record<string, string> = {
    ...(fetchOptions.headers as Record<string, string>),
  };

  if (auth) {
    const token = Cookies.get("access_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = body.detail;
    const message =
      Array.isArray(detail)
        ? detail.map((e: { msg?: string; loc?: string[] }) =>
            `${e.loc?.slice(-1)[0] ?? "字段"}: ${e.msg ?? "校验失败"}`
          ).join("; ")
        : (detail ?? "请求失败");
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── 认证 ────────────────────────────────────────────────────
export const authApi = {
  register: (email: string, password: string, phone?: string) =>
    apiFetch<User>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, ...(phone ? { phone } : {}) }),
      auth: false,
    }),

  login: async (email: string, password: string): Promise<TokenResponse> => {
    const res = await apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      auth: false,
    });
    Cookies.set("access_token", res.access_token, {
      expires: 1,
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict",
    });
    return res;
  },

  logout: () => {
    Cookies.remove("access_token");
  },

  me: () => apiFetch<User>("/auth/me"),

  giveConsent: (version = "1.0") =>
    apiFetch<User>("/auth/consent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version }),
    }),

  refresh: () =>
    apiFetch<TokenResponse>("/auth/refresh", { method: "POST" }),

  changePassword: (currentPassword: string, newPassword: string) =>
    apiFetch<User>("/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),

  sendCode: (channel: "email" | "sms", target: string) =>
    apiFetch<{ message: string }>("/auth/send-code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, target }),
      auth: false,
    }),

  verifyCode: (channel: "email" | "sms", target: string, code: string) =>
    apiFetch<{ message: string; verified: boolean }>("/auth/verify-code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, target, code }),
      auth: false,
    }),

  forgotPassword: (channel: "email" | "sms", target: string) =>
    apiFetch<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, target }),
      auth: false,
    }),

  resetPassword: (channel: "email" | "sms", target: string, code: string, newPassword: string) =>
    apiFetch<{ message: string }>("/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, target, code, new_password: newPassword }),
      auth: false,
    }),
};

// ── 样本上传 ─────────────────────────────────────────────────
export const sampleApi = {
  uploadIdat: (
    redFile: File,
    grnFile: File,
    arrayType: "EPIC" | "450K",
    chronologicalAge: number,
  ) => {
    const form = new FormData();
    form.append("red_channel", redFile);
    form.append("grn_channel", grnFile);
    form.append("array_type", arrayType);
    form.append("chronological_age", String(chronologicalAge));
    return apiFetch<SampleUploadResponse>("/samples/upload/idat", {
      method: "POST",
      body: form,
    });
  },

  uploadBetaCsv: (file: File, arrayType: "EPIC" | "450K", chronologicalAge: number) => {
    const form = new FormData();
    form.append("beta_csv", file);
    form.append("array_type", arrayType);
    form.append("chronological_age", String(chronologicalAge));
    return apiFetch<SampleUploadResponse>("/samples/upload/beta-csv", {
      method: "POST",
      body: form,
    });
  },

  list: () => apiFetch<Sample[]>("/samples"),

  delete: (sampleId: string) =>
    apiFetch<void>(`/samples/${sampleId}`, { method: "DELETE" }),
};

// ── 分析任务 ─────────────────────────────────────────────────
export const jobApi = {
  status: (jobId: string) => apiFetch<JobStatus>(`/jobs/${jobId}/status`),
  result: (jobId: string) => apiFetch<AnalysisResult>(`/jobs/${jobId}/result`),
};

// ── 报告 ──────────────────────────────────────────────────────
export const reportApi = {
  get: (jobId: string) => apiFetch<ReportData>(`/reports/${jobId}`),
  pdfUrl: (jobId: string) =>
    `${API_BASE}/api/v1/reports/${jobId}/pdf?token=${Cookies.get("access_token") ?? ""}`,
};

// ── OAuth 第三方登录 ────────────────────────────────────────────
export const oauthApi = {
  providers: () =>
    apiFetch<{ providers: { name: string; configured: boolean; label: string }[] }>(
      "/auth/oauth/providers",
      { auth: false },
    ),

  getAuthorizeUrl: (provider: string) =>
    apiFetch<{ authorize_url: string; state: string }>(
      `/auth/oauth/${provider}/authorize`,
      { auth: false },
    ),
};

// ── 纵向对比 ───────────────────────────────────────────────────
export const trendApi = {
  get: () => apiFetch<TrendResponse>("/trends"),
};

// ── 管理员用户管理 ──────────────────────────────────────────────
export const adminUserApi = {
  list: (skip = 0, limit = 50) =>
    apiFetch<AdminUserList>(`/admin/users?skip=${skip}&limit=${limit}`),

  setRole: (userId: string, isAdmin: boolean) =>
    apiFetch<AdminUser>(`/admin/users/${userId}/role`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_admin: isAdmin }),
    }),

  setStatus: (userId: string, isActive: boolean) =>
    apiFetch<AdminUser>(`/admin/users/${userId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: isActive }),
    }),
};

// ── 管理员知识库 ───────────────────────────────────────────────
export const knowledgeApi = {
  list: (params?: { skip?: number; limit?: number; status_filter?: string }) => {
    const qs = new URLSearchParams();
    if (params?.skip !== undefined) qs.set("skip", String(params.skip));
    if (params?.limit !== undefined) qs.set("limit", String(params.limit));
    if (params?.status_filter) qs.set("status_filter", params.status_filter);
    const query = qs.toString() ? `?${qs}` : "";
    return apiFetch<KnowledgeDocumentList>(`/admin/knowledge${query}`);
  },

  get: (docId: string) =>
    apiFetch<KnowledgeDocument>(`/admin/knowledge/${docId}`),

  upload: (
    file: File,
    meta: {
      title: string;
      description?: string;
      authors?: string;
      journal?: string;
      published_year?: number;
      doi?: string;
      tags?: string;
    },
  ) => {
    const form = new FormData();
    form.append("file", file);
    form.append("title", meta.title);
    if (meta.description) form.append("description", meta.description);
    if (meta.authors) form.append("authors", meta.authors);
    if (meta.journal) form.append("journal", meta.journal);
    if (meta.published_year !== undefined)
      form.append("published_year", String(meta.published_year));
    if (meta.doi) form.append("doi", meta.doi);
    if (meta.tags) form.append("tags", meta.tags);
    return apiFetch<KnowledgeDocument>("/admin/knowledge", { method: "POST", body: form });
  },

  delete: (docId: string) =>
    apiFetch<void>(`/admin/knowledge/${docId}`, { method: "DELETE" }),

  reprocess: (docId: string) =>
    apiFetch<KnowledgeDocument>(`/admin/knowledge/${docId}/reprocess`, { method: "POST" }),

  search: (query: string, topK = 5, scoreThreshold = 0.3) =>
    apiFetch<SearchResponse>("/admin/knowledge/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK, score_threshold: scoreThreshold }),
    }),
};
