/**
 * 小程序 API 客户端
 *
 * 与 Web 端 api.ts 保持接口一致，但底层使用 Taro.request（wx.request）
 * 而非 fetch，以兼容微信小程序运行时。
 */
import Taro from "@tarojs/taro";

// 后端 API 地址 — 生产环境替换为真实域名
// 小程序必须使用 HTTPS 且域名已在微信公众平台备案
const API_BASE = process.env.TARO_APP_API_BASE ?? "https://api.yourdomain.com";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// ── Token 管理（小程序用 wx.setStorageSync 替代 localStorage）──

export const TokenStore = {
  get: () => Taro.getStorageSync<string>("access_token") || null,
  set: (token: string) => Taro.setStorageSync("access_token", token),
  clear: () => Taro.removeStorageSync("access_token"),
};

// ── 通用请求函数 ───────────────────────────────────────────────

async function request<T>(
  path: string,
  options: Taro.request.Option & { auth?: boolean } = {},
): Promise<T> {
  const { auth = true, ...reqOptions } = options;
  const header: Record<string, string> = {
    "Content-Type": "application/json",
    ...(reqOptions.header as Record<string, string>),
  };

  if (auth) {
    const token = TokenStore.get();
    if (token) header["Authorization"] = `Bearer ${token}`;
  }

  const res = await Taro.request<T>({
    url: `${API_BASE}/api/v1${path}`,
    header,
    ...reqOptions,
  });

  if (res.statusCode >= 400) {
    const body = res.data as { detail?: string | Array<{ msg: string; loc: string[] }> };
    const detail = body?.detail;
    const message =
      Array.isArray(detail)
        ? detail.map((e) => `${e.loc?.slice(-1)[0]}: ${e.msg}`).join("; ")
        : (detail as string) ?? "请求失败";
    throw new ApiError(res.statusCode, message);
  }

  return res.data as T;
}

// ── 认证接口 ────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/**
 * 微信小程序一键登录
 * 1. 调用 wx.login() 拿到 code
 * 2. POST 到后端 /auth/wechat-miniapp/login
 * 3. 后端换 openid，自动创建账号，返回 JWT
 */
export async function wechatLogin(): Promise<TokenResponse> {
  const { code } = await Taro.login();
  const data = await request<TokenResponse>("/auth/wechat-miniapp/login", {
    method: "POST",
    data: { code },
    auth: false,
  });
  TokenStore.set(data.access_token);
  return data;
}

export async function getMe() {
  return request<{ id: string; email: string; avatar_url: string | null }>("/auth/me");
}

export async function postConsent(version: string) {
  return request("/auth/consent", {
    method: "POST",
    data: { version, agreed: true },
  });
}

// ── 样本上传 ─────────────────────────────────────────────────────

export interface SampleUploadResponse {
  sample_id: string;
  job_id: string;
  status: string;
}

/**
 * 上传 Beta CSV 文件
 * 小程序使用 Taro.uploadFile（wx.uploadFile）而非 fetch FormData
 * IDAT 双文件需要两次调用，或使用预签名 URL 直传 MinIO
 */
export async function uploadBetaCsv(filePath: string): Promise<SampleUploadResponse> {
  const token = TokenStore.get();
  const res = await Taro.uploadFile({
    url: `${API_BASE}/api/v1/samples/upload/beta-csv`,
    filePath,
    name: "file",
    header: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (res.statusCode >= 400) {
    throw new ApiError(res.statusCode, "文件上传失败，请检查文件格式");
  }

  return JSON.parse(res.data) as SampleUploadResponse;
}

/**
 * 获取 MinIO 预签名直传 URL（用于 IDAT 大文件，绕过后端中转，减小后端压力）
 */
export async function getUploadPresignedUrl(filename: string, contentType: string) {
  return request<{ upload_url: string; object_key: string }>(
    `/samples/presign-upload?filename=${encodeURIComponent(filename)}&content_type=${encodeURIComponent(contentType)}`,
  );
}

// ── 分析任务 ─────────────────────────────────────────────────────

export interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  return request<JobStatus>(`/jobs/${jobId}/status`);
}

// ── 报告 ─────────────────────────────────────────────────────────

export interface ClockResult {
  clock_name: string;
  biological_age: number | null;
  chronological_age: number | null;
  age_acceleration: number | null;
}

export interface DimensionScore {
  name: string;
  score: number;
  label: string;
}

export interface ReportData {
  job_id: string;
  clocks: ClockResult[];
  dunedin_pace: number | null;
  dimension_scores: DimensionScore[];
  recommendations: Recommendation[];
  ai_summary: string | null;
  created_at: string;
}

export interface Recommendation {
  id: string;
  title: string;
  category: string;
  evidence_level: string;
  summary: string;
  pmid: string | null;
}

export async function getReport(reportId: string): Promise<ReportData> {
  return request<ReportData>(`/reports/${reportId}`);
}

export async function getSamples() {
  return request<{ samples: Array<{ id: string; filename: string; created_at: string }> }>(
    "/samples",
  );
}

// ── AI 问答 ─────────────────────────────────────────────────────

export async function chatWithAI(jobId: string, message: string) {
  return request<{ answer: string; sources: string[] }>("/chat", {
    method: "POST",
    data: { job_id: jobId, message },
  });
}
