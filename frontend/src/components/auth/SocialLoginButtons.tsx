"use client";

import { useEffect, useState } from "react";
import { oauthApi } from "@/lib/api";

const PROVIDER_STYLES: Record<string, { icon: string; bg: string; text: string; hover: string }> = {
  github: {
    icon: "M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.009-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.607.069-.607 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z",
    bg: "bg-gray-900",
    text: "text-white",
    hover: "hover:bg-gray-800",
  },
  google: {
    icon: "M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z",
    bg: "bg-white border border-gray-200",
    text: "text-gray-700",
    hover: "hover:bg-gray-50",
  },
  wechat: {
    icon: "M9.5 4C5.36 4 2 6.69 2 10c0 1.89 1.08 3.56 2.78 4.66l-.7 2.1 2.46-1.23c.78.21 1.6.32 2.46.32.34 0 .68-.02 1-.06-.21-.68-.33-1.4-.33-2.14C9.67 9.88 12.24 7 15.5 7c.39 0 .77.04 1.14.1C15.83 5.25 12.93 4 9.5 4zm-3 4.5a1 1 0 110-2 1 1 0 010 2zm5 0a1 1 0 110-2 1 1 0 010 2zM22 13.65c0-2.74-2.81-4.97-6.25-4.97S9.5 10.91 9.5 13.65c0 2.74 2.81 4.97 6.25 4.97.66 0 1.3-.08 1.9-.24l1.89.95-.54-1.62C20.94 16.83 22 15.36 22 13.65zm-8.25-1a.87.87 0 110-1.75.87.87 0 010 1.75zm4 0a.87.87 0 110-1.75.87.87 0 010 1.75z",
    bg: "bg-green-600",
    text: "text-white",
    hover: "hover:bg-green-700",
  },
};

export default function SocialLoginButtons() {
  const [providers, setProviders] = useState<{ name: string; configured: boolean; label: string }[]>([]);
  const [loading, setLoading] = useState<string | null>(null);

  useEffect(() => {
    oauthApi.providers().then((res) => setProviders(res.providers)).catch(() => {});
  }, []);

  const configured = providers.filter((p) => p.configured);
  if (configured.length === 0) return null;

  const handleClick = async (providerName: string) => {
    setLoading(providerName);
    try {
      const { authorize_url } = await oauthApi.getAuthorizeUrl(providerName);
      window.location.href = authorize_url;
    } catch {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-gray-200" />
        <span className="text-xs text-gray-400">或使用第三方账号</span>
        <div className="flex-1 h-px bg-gray-200" />
      </div>

      <div className="flex flex-col gap-2">
        {configured.map((p) => {
          const style = PROVIDER_STYLES[p.name];
          if (!style) return null;
          return (
            <button
              key={p.name}
              onClick={() => handleClick(p.name)}
              disabled={loading === p.name}
              className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium
                         transition disabled:opacity-50 ${style.bg} ${style.text} ${style.hover}`}
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path d={style.icon} />
              </svg>
              {loading === p.name ? "跳转中..." : `${p.label} 登录`}
            </button>
          );
        })}
      </div>
    </div>
  );
}
