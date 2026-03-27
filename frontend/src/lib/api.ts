import Cookies from "js-cookie";
import type {
  AnalysisResult,
  JobStatus,
  ReportData,
  Sample,
  SampleUploadResponse,
  TokenResponse,
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
  register: (email: string, password: string) =>
    apiFetch<User>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
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
