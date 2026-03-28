/**
 * JWT Token 自动刷新
 *
 * 在 Token 到期前 5 分钟自动续签，避免用户操作中途被踢出。
 * 调用方式：在 layout 或 Navbar 中 useTokenRefresh()
 */

import { useEffect, useRef } from "react";
import Cookies from "js-cookie";
import { authApi } from "@/lib/api";

// Token 有效期（秒），与后端 jwt_access_expire_minutes 对齐
const TOKEN_TTL_SECONDS = 3600;
// 提前刷新的秒数
const REFRESH_BEFORE_SECONDS = 300; // 5 分钟

export function useTokenRefresh() {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const scheduleRefresh = () => {
      const delay = (TOKEN_TTL_SECONDS - REFRESH_BEFORE_SECONDS) * 1000;

      timerRef.current = setTimeout(async () => {
        try {
          const token = Cookies.get("access_token");
          if (!token) return; // 未登录

          const res = await authApi.refresh();
          Cookies.set("access_token", res.access_token, {
            expires: 1,
            secure: process.env.NODE_ENV === "production",
            sameSite: "strict",
          });
          // 续签成功，安排下一次刷新
          scheduleRefresh();
        } catch {
          // 刷新失败（Token 已过期），不重试
        }
      }, delay);
    };

    // 仅在已登录时启动
    if (Cookies.get("access_token")) {
      scheduleRefresh();
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);
}
