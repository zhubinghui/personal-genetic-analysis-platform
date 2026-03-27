"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi, ApiError } from "@/lib/api";

export default function ConsentPage() {
  const router = useRouter();
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleConsent = async () => {
    setLoading(true);
    try {
      await authApi.giveConsent();
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "提交失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow p-8 space-y-6">
        <h1 className="text-2xl font-bold text-gray-800">知情同意书</h1>

        <div className="prose text-sm text-gray-600 space-y-4 max-h-96 overflow-y-auto border rounded-lg p-4 bg-gray-50">
          <h3 className="font-semibold text-gray-800">数据收集与使用</h3>
          <p>本平台收集您上传的血液 DNA 甲基化数据（IDAT 文件或 beta 值矩阵），用于计算生物学年龄和衰老速率指标，并提供个性化抗衰老建议。</p>

          <h3 className="font-semibold text-gray-800">隐私保护措施</h3>
          <ul className="list-disc ml-4 space-y-1">
            <li>您的基因数据采用 AES-256-GCM 加密存储，密钥与数据分离管理</li>
            <li>您的身份信息与基因数据通过假名化（pseudonymization）技术隔离</li>
            <li>您的数据不会被用于模型训练或与第三方共享（除非您单独明确授权）</li>
            <li>您的基因数据永远不会出境传输</li>
          </ul>

          <h3 className="font-semibold text-gray-800">您的权利</h3>
          <ul className="list-disc ml-4 space-y-1">
            <li><strong>访问权</strong>：随时查看您上传的数据和分析结果</li>
            <li><strong>删除权</strong>：可随时删除您的所有数据（包括加密存储的原始文件）</li>
            <li><strong>撤回同意权</strong>：可随时撤回本同意书，不影响此前数据处理的合法性</li>
          </ul>

          <h3 className="font-semibold text-gray-800">免责声明</h3>
          <p>本平台提供的所有分析结果和建议仅供健康管理参考，<strong>不构成医疗诊断或治疗建议</strong>。如有健康问题请咨询专业医生。</p>

          <p className="text-xs text-gray-400">知情同意书版本 1.0 | 生效日期：2026-01-01</p>
        </div>

        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="agree"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="mt-1 h-4 w-4 accent-brand-600"
          />
          <label htmlFor="agree" className="text-sm text-gray-700">
            我已阅读并理解上述知情同意书，同意平台按照说明处理我的数据
          </label>
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button
          onClick={handleConsent}
          disabled={!agreed || loading}
          className="w-full bg-brand-600 text-white py-3 rounded-lg hover:bg-brand-700 disabled:opacity-40 transition font-medium"
        >
          {loading ? "提交中..." : "同意并继续"}
        </button>
      </div>
    </div>
  );
}
