/**
 * 登录页
 *
 * 微信小程序特有优势：用户只需点一下「微信一键登录」，
 * 无需输入账号密码——wx.login() 静默获取 code，后端自动创建账号。
 */
import { View, Text, Image, Button } from "@tarojs/components";
import Taro, { useLoad } from "@tarojs/taro";
import { useState } from "react";
import { wechatLogin, getMe, TokenStore } from "../../lib/api";
import "./index.scss";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useLoad(() => {
    // 已登录则直接跳转
    const token = TokenStore.get();
    if (token) {
      Taro.switchTab({ url: "/pages/index/index" });
    }
  });

  const handleWechatLogin = async () => {
    setLoading(true);
    setError("");
    try {
      await wechatLogin();
      const user = await getMe();

      // 首次登录 → 跳同意页；已同意 → 跳首页
      const hasConsented = Taro.getStorageSync("consented");
      if (!hasConsented) {
        Taro.navigateTo({ url: "/pages/consent/index" });
      } else {
        Taro.switchTab({ url: "/pages/index/index" });
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "登录失败，请重试";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View className="login-page">
      <View className="hero">
        <View className="logo-wrap">
          {/* DNA 螺旋图标占位 */}
          <View className="logo-icon">🧬</View>
        </View>
        <Text className="title">基因衰老分析</Text>
        <Text className="subtitle">科学解读您的表观遗传衰老速率</Text>
      </View>

      <View className="features">
        {[
          { icon: "⏱", label: "4 个衰老时钟" },
          { icon: "🔬", label: "9 大生理维度" },
          { icon: "🔒", label: "隐私加密保护" },
        ].map((f) => (
          <View key={f.label} className="feature-item">
            <Text className="feature-icon">{f.icon}</Text>
            <Text className="feature-label">{f.label}</Text>
          </View>
        ))}
      </View>

      {error ? <Text className="error-tip">{error}</Text> : null}

      {/* 微信一键登录 — 无需输入任何信息 */}
      <Button
        className="wx-login-btn"
        loading={loading}
        disabled={loading}
        onClick={handleWechatLogin}
      >
        {loading ? "登录中..." : "微信一键登录"}
      </Button>

      <Text className="disclaimer">
        登录即表示您同意《隐私政策》和《用户协议》{"\n"}
        本平台结果仅供健康管理参考，不构成医疗诊断
      </Text>
    </View>
  );
}
