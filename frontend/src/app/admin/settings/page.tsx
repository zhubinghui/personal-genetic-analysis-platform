"use client";

import { useEffect, useState } from "react";
import { settingsApi, ApiError } from "@/lib/api";

/* ── Provider 图标（内联 SVG）────────────────────── */

function ClaudeIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.154 3.041c-.376-.133-1.058-.248-1.565-.248-2.556 0-4.298 1.6-4.993 3.648l-.1.294-.1-.294C9.702 4.393 7.96 2.793 5.404 2.793c-.507 0-1.189.115-1.565.248C1.636 3.906.266 6.11.266 8.72c0 4.726 5.26 9.95 9.413 12.56.585.367 1.24.72 1.817.72h1.008c.577 0 1.232-.353 1.817-.72 4.153-2.61 9.413-7.834 9.413-12.56 0-2.61-1.37-4.814-3.573-5.679h-.007z"/>
    </svg>
  );
}

function OpenAIIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z"/>
    </svg>
  );
}

function DeepSeekIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <circle cx="12" cy="12" r="10" fill="#4D6BFE" />
      <text x="12" y="16" textAnchor="middle" fill="white" fontSize="10" fontWeight="bold" fontFamily="sans-serif">DS</text>
    </svg>
  );
}

function KimiIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <circle cx="12" cy="12" r="10" fill="#1A1A2E" />
      <path d="M8 8l4 4-4 4M13 16h4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
    </svg>
  );
}

function QWenIcon({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <circle cx="12" cy="12" r="10" fill="#615EF0" />
      <text x="12" y="16" textAnchor="middle" fill="white" fontSize="9" fontWeight="bold" fontFamily="sans-serif">QW</text>
    </svg>
  );
}

const PROVIDER_ICONS: Record<string, React.FC<{ className?: string }>> = {
  claude: ClaudeIcon, openai: OpenAIIcon, deepseek: DeepSeekIcon, kimi: KimiIcon, qwen: QWenIcon,
};

const PROVIDERS = [
  { name: "",         label: "请选择模型提供商...", placeholder: "", defaultModel: "", defaultBaseUrl: "", helpUrl: "" },
  { name: "claude",   label: "Claude (Anthropic)", placeholder: "sk-ant-api03-...", defaultModel: "claude-sonnet-4-20250514", defaultBaseUrl: "", helpUrl: "console.anthropic.com → API Keys" },
  { name: "openai",   label: "ChatGPT (OpenAI)",   placeholder: "sk-proj-...", defaultModel: "gpt-4o", defaultBaseUrl: "", helpUrl: "platform.openai.com → API Keys" },
  { name: "deepseek", label: "DeepSeek",           placeholder: "sk-...", defaultModel: "deepseek-chat", defaultBaseUrl: "https://api.deepseek.com", helpUrl: "platform.deepseek.com → API Keys" },
  { name: "kimi",     label: "Kimi (Moonshot)",     placeholder: "sk-...", defaultModel: "moonshot-v1-8k", defaultBaseUrl: "https://api.moonshot.cn/v1", helpUrl: "platform.moonshot.cn → API Key 管理" },
  { name: "qwen",     label: "通义千问 (QWen)",      placeholder: "sk-...", defaultModel: "qwen-plus", defaultBaseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", helpUrl: "dashscope.console.aliyun.com → API-KEY 管理" },
];

const NEEDS_BASE_URL = ["deepseek", "kimi", "qwen"];

export default function AdminSettingsPage() {
  const [provider, setProvider] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [temperature, setTemperature] = useState(0.3);
  const [maxTokens, setMaxTokens] = useState(2000);
  const [currentMasked, setCurrentMasked] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  useEffect(() => {
    settingsApi.getLLM().then((data: any) => {
      setProvider(data.provider || "");
      setModel(data.model || "");
      setBaseUrl(data.base_url || "");
      setTemperature(data.temperature ?? 0.3);
      setMaxTokens(data.max_tokens ?? 2000);
      setCurrentMasked(data.api_key_masked || "");
    }).catch(() => {});
  }, []);

  const selectedProvider = PROVIDERS.find((p) => p.name === provider);
  const ProviderIcon = provider ? PROVIDER_ICONS[provider] : null;

  const handleProviderChange = (name: string) => {
    setProvider(name);
    const p = PROVIDERS.find((x) => x.name === name);
    if (p) {
      if (!model || PROVIDERS.some((x) => x.defaultModel === model)) setModel(p.defaultModel);
      setBaseUrl(p.defaultBaseUrl);
    }
    setFeedback(null);
  };

  const handleSave = async () => {
    if (!provider) { setFeedback({ type: "error", msg: "请先选择模型提供商" }); return; }
    setSaving(true);
    setFeedback(null);
    try {
      await settingsApi.updateLLM({
        provider, api_key: apiKey || undefined, model,
        base_url: baseUrl, temperature, max_tokens: maxTokens,
      });
      if (apiKey) setCurrentMasked(apiKey.slice(0, 8) + "..." + apiKey.slice(-4));
      setApiKey("");
      setFeedback({ type: "success", msg: "设置已保存" });
      setTimeout(() => setFeedback(null), 4000);
    } catch (e) {
      setFeedback({ type: "error", msg: e instanceof ApiError ? e.message : "保存失败，请检查网络连接" });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!provider) { setFeedback({ type: "error", msg: "请先选择模型提供商" }); return; }
    if (!apiKey && !currentMasked) { setFeedback({ type: "error", msg: "请先填写并保存 API Key" }); return; }
    setTesting(true);
    setFeedback(null);
    try {
      const res = await settingsApi.testLLM();
      setFeedback({ type: "success", msg: `连接成功！${res.provider} 回复: "${res.response}"` });
    } catch (e) {
      const detail = e instanceof ApiError ? e.message : "连接失败";
      setFeedback({ type: "error", msg: `测试失败: ${detail}` });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-10 px-4 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">系统设置</h1>
        <p className="text-sm text-gray-500 mt-1">配置 AI 大模型用于报告解读和知识库问答</p>
      </div>

      {/* 当前状态卡片 */}
      <div className={`card p-4 flex items-center gap-4 ${provider && currentMasked ? "bg-green-50 border-green-200" : "bg-amber-50 border-amber-200"}`}>
        <div className="text-2xl shrink-0">
          {provider && currentMasked ? (ProviderIcon ? <ProviderIcon className="w-8 h-8" /> : "✅") : "⚠️"}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-800">
            {provider && currentMasked ? `当前使用: ${selectedProvider?.label ?? provider}` : "AI 功能未配置"}
          </p>
          <p className="text-xs text-gray-500 truncate">
            {provider && currentMasked
              ? `模型: ${model || selectedProvider?.defaultModel} · Key: ${currentMasked}`
              : "请选择模型提供商并填写 API Key，以启用 AI 报告解读和 Chatbot 功能"}
          </p>
        </div>
      </div>

      {/* 配置表单 */}
      <div className="card p-6 space-y-6">

        {/* 第一步：选择提供商 */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 bg-brand-600 text-white rounded-full text-xs flex items-center justify-center font-bold shrink-0">1</span>
            <label className="text-sm font-semibold text-gray-800">选择模型提供商</label>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {PROVIDERS.filter(p => p.name).map((p) => {
              const Icon = PROVIDER_ICONS[p.name];
              return (
                <button
                  key={p.name}
                  onClick={() => handleProviderChange(p.name)}
                  className={`flex items-center gap-2 py-2.5 px-3 rounded-xl text-sm font-medium border transition ${
                    provider === p.name
                      ? "border-brand-500 bg-brand-50 text-brand-700 shadow-sm"
                      : "border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {Icon && <Icon className="w-4 h-4 shrink-0" />}
                  <span className="truncate">{p.label.split(" (")[0]}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* 第二步：填写 API Key（选择 provider 后显示） */}
        {provider && (
          <div className="space-y-4 pl-8 border-l-2 border-brand-100">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 bg-brand-600 text-white rounded-full text-xs flex items-center justify-center font-bold shrink-0">2</span>
                <label className="text-sm font-semibold text-gray-800">填写 API Key</label>
              </div>
              {currentMasked && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full">已配置</span>
                  <span className="text-gray-400 font-mono">{currentMasked}</span>
                </div>
              )}
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={selectedProvider?.placeholder || "输入 API Key"}
                className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm bg-gray-50
                           focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
              />
              {selectedProvider?.helpUrl && (
                <p className="text-xs text-gray-400">获取方式: {selectedProvider.helpUrl}</p>
              )}
            </div>

            {/* 第三步：高级设置 */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 bg-gray-300 text-white rounded-full text-xs flex items-center justify-center font-bold shrink-0">3</span>
                <label className="text-sm font-semibold text-gray-800">高级设置 <span className="text-gray-400 font-normal text-xs">（可选）</span></label>
              </div>

              <div className={`grid gap-4 ${NEEDS_BASE_URL.includes(provider) ? "grid-cols-2" : "grid-cols-1"}`}>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">模型名称</label>
                  <input
                    type="text" value={model} onChange={(e) => setModel(e.target.value)}
                    placeholder={selectedProvider?.defaultModel || "默认模型"}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50
                               focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
                  />
                </div>
                {NEEDS_BASE_URL.includes(provider) && (
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">API Base URL</label>
                    <input
                      type="text" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
                      placeholder={selectedProvider?.defaultBaseUrl}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50
                                 focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
                    />
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">
                    Temperature: <span className="text-brand-600 font-semibold">{temperature}</span>
                    <span className="text-gray-400 ml-1">{temperature <= 0.2 ? "(精确)" : temperature <= 0.5 ? "(平衡)" : "(创意)"}</span>
                  </label>
                  <input type="range" min={0} max={1} step={0.1} value={temperature}
                    onChange={(e) => setTemperature(Number(e.target.value))} className="w-full accent-brand-600" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">最大 Tokens</label>
                  <input type="number" value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50
                               focus:outline-none focus:ring-2 focus:ring-brand-500 transition" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex gap-3 pt-3 border-t border-gray-100">
          <button onClick={handleSave} disabled={saving || !provider}
            className="flex-1 py-2.5 bg-brand-600 text-white rounded-xl font-medium hover:bg-brand-700 disabled:opacity-50 transition shadow-sm">
            {saving ? "保存中..." : "保存设置"}
          </button>
          <button onClick={handleTest} disabled={testing || !provider}
            className="px-5 py-2.5 border border-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-50 disabled:opacity-50 transition">
            {testing ? (
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                测试中
              </span>
            ) : "测试连接"}
          </button>
        </div>

        {/* 反馈消息 */}
        {feedback && (
          <div className={`px-4 py-3 rounded-xl text-sm flex items-start gap-2 ${
            feedback.type === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"
          }`}>
            <span className="shrink-0 mt-0.5">{feedback.type === "success" ? "✓" : "✗"}</span>
            <span>{feedback.msg}</span>
          </div>
        )}
      </div>
    </div>
  );
}
