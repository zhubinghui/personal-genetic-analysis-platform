"use client";

import { useEffect, useState } from "react";
import { settingsApi, ApiError } from "@/lib/api";

const PROVIDERS = [
  { name: "",         label: "请选择模型提供商...",   icon: "",   placeholder: "", defaultModel: "", defaultBaseUrl: "" },
  { name: "claude",   label: "Claude (Anthropic)",  icon: "🟣", placeholder: "sk-ant-...", defaultModel: "claude-sonnet-4-20250514", defaultBaseUrl: "" },
  { name: "openai",   label: "ChatGPT (OpenAI)",    icon: "🟢", placeholder: "sk-...", defaultModel: "gpt-4o", defaultBaseUrl: "" },
  { name: "deepseek", label: "DeepSeek",            icon: "🔵", placeholder: "sk-...", defaultModel: "deepseek-chat", defaultBaseUrl: "https://api.deepseek.com" },
  { name: "kimi",     label: "Kimi (Moonshot)",      icon: "🟠", placeholder: "sk-...", defaultModel: "moonshot-v1-8k", defaultBaseUrl: "https://api.moonshot.cn/v1" },
];

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
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [message, setMessage] = useState("");

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

  const handleProviderChange = (name: string) => {
    setProvider(name);
    const p = PROVIDERS.find((x) => x.name === name);
    if (p) {
      if (!model || PROVIDERS.some((x) => x.defaultModel === model)) {
        setModel(p.defaultModel);
      }
      setBaseUrl(p.defaultBaseUrl);
    }
    setTestResult(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage("");
    try {
      await settingsApi.updateLLM({
        provider,
        api_key: apiKey || undefined,
        model,
        base_url: baseUrl,
        temperature,
        max_tokens: maxTokens,
      });
      setMessage("设置已保存");
      if (apiKey) setCurrentMasked(apiKey.slice(0, 8) + "..." + apiKey.slice(-4));
      setApiKey("");
      setTimeout(() => setMessage(""), 3000);
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await settingsApi.testLLM();
      setTestResult({ ok: true, msg: `连接成功！模型回复: "${res.response}"` });
    } catch (e) {
      setTestResult({ ok: false, msg: e instanceof ApiError ? e.message : "测试失败" });
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
        <div className="text-2xl">
          {provider && currentMasked ? "✅" : "⚠️"}
        </div>
        <div>
          <p className="text-sm font-medium text-gray-800">
            {provider && currentMasked
              ? `当前使用: ${selectedProvider?.label ?? provider}`
              : "AI 功能未配置"
            }
          </p>
          <p className="text-xs text-gray-500">
            {provider && currentMasked
              ? `模型: ${model || selectedProvider?.defaultModel} · Key: ${currentMasked}`
              : "请选择模型提供商并填写 API Key，以启用 AI 报告解读和 Chatbot 功能"
            }
          </p>
        </div>
      </div>

      {/* 配置表单 */}
      <div className="card p-6 space-y-6">

        {/* 第一步：选择提供商 */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 bg-brand-600 text-white rounded-full text-xs flex items-center justify-center font-bold">1</span>
            <label className="text-sm font-semibold text-gray-800">选择模型提供商</label>
          </div>
          <select
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value)}
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm bg-white
                       focus:outline-none focus:ring-2 focus:ring-brand-500 transition appearance-none
                       cursor-pointer"
            style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M6 8L1 3h10z'/%3E%3C/svg%3E\")", backgroundRepeat: "no-repeat", backgroundPosition: "right 16px center" }}
          >
            {PROVIDERS.map((p) => (
              <option key={p.name} value={p.name}>
                {p.icon} {p.label}
              </option>
            ))}
          </select>
        </div>

        {/* 第二步：填写 API Key（选择 provider 后显示） */}
        {provider && (
          <div className="space-y-4 pl-8 border-l-2 border-brand-100">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 bg-brand-600 text-white rounded-full text-xs flex items-center justify-center font-bold">2</span>
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
              <p className="text-xs text-gray-400">
                {provider === "claude" && "获取方式: console.anthropic.com → API Keys"}
                {provider === "openai" && "获取方式: platform.openai.com → API Keys"}
                {provider === "deepseek" && "获取方式: platform.deepseek.com → API Keys"}
                {provider === "kimi" && "获取方式: platform.moonshot.cn → API Key 管理"}
              </p>
            </div>

            {/* 第三步：高级设置 */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 bg-gray-300 text-white rounded-full text-xs flex items-center justify-center font-bold">3</span>
                <label className="text-sm font-semibold text-gray-800">高级设置 <span className="text-gray-400 font-normal text-xs">（可选）</span></label>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">模型名称</label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder={selectedProvider?.defaultModel || "默认模型"}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50
                               focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
                  />
                </div>

                {(provider === "deepseek" || provider === "kimi") && (
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-gray-600">API Base URL</label>
                    <input
                      type="text"
                      value={baseUrl}
                      onChange={(e) => setBaseUrl(e.target.value)}
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
                  <input
                    type="range" min={0} max={1} step={0.1}
                    value={temperature}
                    onChange={(e) => setTemperature(Number(e.target.value))}
                    className="w-full accent-brand-600"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-600">最大 Tokens</label>
                  <input
                    type="number"
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(Number(e.target.value))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50
                               focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex gap-3 pt-3 border-t border-gray-100">
          <button
            onClick={handleSave}
            disabled={saving || !provider}
            className="flex-1 py-2.5 bg-brand-600 text-white rounded-xl font-medium
                       hover:bg-brand-700 disabled:opacity-50 transition shadow-sm"
          >
            {saving ? "保存中..." : "保存设置"}
          </button>
          <button
            onClick={handleTest}
            disabled={testing || !provider || (!apiKey && !currentMasked)}
            className="px-5 py-2.5 border border-gray-200 text-gray-700 rounded-xl font-medium
                       hover:bg-gray-50 disabled:opacity-50 transition"
          >
            {testing ? (
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                测试中
              </span>
            ) : "测试连接"}
          </button>
        </div>

        {/* 反馈消息 */}
        {message && (
          <div className="px-4 py-2.5 rounded-xl text-sm bg-green-50 text-green-700 flex items-center gap-2">
            <span>✓</span> {message}
          </div>
        )}

        {testResult && (
          <div className={`px-4 py-3 rounded-xl text-sm flex items-center gap-2 ${
            testResult.ok ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
          }`}>
            <span>{testResult.ok ? "✓" : "✗"}</span>
            {testResult.msg}
          </div>
        )}
      </div>
    </div>
  );
}
