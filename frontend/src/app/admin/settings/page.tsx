"use client";

import { useEffect, useState } from "react";
import { settingsApi, ApiError } from "@/lib/api";

const PROVIDERS = [
  { name: "claude", label: "Claude (Anthropic)", placeholder: "sk-ant-..." },
  { name: "openai", label: "ChatGPT (OpenAI)", placeholder: "sk-..." },
  { name: "deepseek", label: "DeepSeek", placeholder: "sk-..." },
  { name: "kimi", label: "Kimi (Moonshot)", placeholder: "sk-..." },
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
      setMessage("保存成功");
      if (apiKey) setCurrentMasked(apiKey.slice(0, 8) + "...");
      setApiKey("");
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
      setTestResult({ ok: true, msg: `连接成功 (${res.provider}): ${res.response}` });
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

      <div className="card p-6 space-y-5">
        <h2 className="font-semibold text-gray-800">LLM 大模型配置</h2>

        {/* Provider 选择 */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">模型提供商</label>
          <div className="grid grid-cols-2 gap-2">
            {PROVIDERS.map((p) => (
              <button
                key={p.name}
                onClick={() => setProvider(p.name)}
                className={`py-2.5 px-3 rounded-xl text-sm font-medium border transition ${
                  provider === p.name
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* API Key */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">API Key</label>
          {currentMasked && (
            <p className="text-xs text-gray-400">当前: {currentMasked}</p>
          )}
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={PROVIDERS.find((p) => p.name === provider)?.placeholder || "输入 API Key"}
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm bg-gray-50
                       focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
          />
        </div>

        {/* Model */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">模型名称 <span className="text-gray-400 font-normal">（留空使用默认）</span></label>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="如 claude-sonnet-4-20250514 / gpt-4o / deepseek-chat"
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm bg-gray-50
                       focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
          />
        </div>

        {/* Base URL (for DeepSeek/Kimi) */}
        {(provider === "deepseek" || provider === "kimi") && (
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">API Base URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={provider === "deepseek" ? "https://api.deepseek.com" : "https://api.moonshot.cn/v1"}
              className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm bg-gray-50
                         focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
            />
          </div>
        )}

        {/* 温度 + Max Tokens */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Temperature: {temperature}</label>
            <input
              type="range" min={0} max={1} step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
              className="w-full"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Max Tokens</label>
            <input
              type="number"
              value={maxTokens}
              onChange={(e) => setMaxTokens(Number(e.target.value))}
              className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm bg-gray-50
                         focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
            />
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={saving || !provider}
            className="flex-1 py-2.5 bg-brand-600 text-white rounded-xl font-medium
                       hover:bg-brand-700 disabled:opacity-50 transition"
          >
            {saving ? "保存中..." : "保存设置"}
          </button>
          <button
            onClick={handleTest}
            disabled={testing}
            className="px-4 py-2.5 border border-gray-200 text-gray-700 rounded-xl font-medium
                       hover:bg-gray-50 disabled:opacity-50 transition"
          >
            {testing ? "测试中..." : "测试连接"}
          </button>
        </div>

        {message && <p className="text-sm text-green-600">{message}</p>}

        {testResult && (
          <div className={`px-4 py-3 rounded-xl text-sm ${testResult.ok ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
            {testResult.msg}
          </div>
        )}
      </div>
    </div>
  );
}
