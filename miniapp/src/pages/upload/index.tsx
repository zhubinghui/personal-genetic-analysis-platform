/**
 * 检测上传页
 *
 * 两种上传方式：
 *  A. Beta CSV（数据矩阵，适合有原始数据的用户）
 *  B. 套餐预购（还没做检测的用户 → 引导购买 + 邮寄采样管）
 *
 * 注：IDAT 文件（4-8 MB × 2）使用预签名 URL 直传 MinIO，避免后端中转
 */
import { View, Text, Button } from "@tarojs/components";
import Taro, { useLoad } from "@tarojs/taro";
import { useState } from "react";
import { uploadBetaCsv, getUploadPresignedUrl, TokenStore, ApiError } from "../../lib/api";
import "./index.scss";

type UploadMode = "select" | "uploading" | "success" | "error";

export default function UploadPage() {
  const [mode, setMode] = useState<UploadMode>("select");
  const [jobId, setJobId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [progress, setProgress] = useState(0);

  useLoad(() => {
    if (!TokenStore.get()) {
      Taro.redirectTo({ url: "/pages/login/index" });
    }
  });

  // ── 方式 A：上传 Beta CSV ───────────────────────────────────
  const handleBetaCsvUpload = async () => {
    try {
      // 选择文件（小程序只支持特定类型，CSV 归类到 .csv 或 "all"）
      const res = await Taro.chooseMessageFile({
        count: 1,
        type: "file",
        extension: ["csv"],
      });

      const file = res.tempFiles[0];
      if (file.size > 200 * 1024 * 1024) {
        Taro.showToast({ title: "文件不能超过 200MB", icon: "error" });
        return;
      }

      setMode("uploading");
      setProgress(10);

      const result = await uploadBetaCsv(file.path);
      setJobId(result.job_id);
      setMode("success");

      // 跳转到报告页，传入 job_id，轮询进度
      setTimeout(() => {
        Taro.navigateTo({
          url: `/pages/report/index?jobId=${result.job_id}`,
        });
      }, 1500);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "上传失败，请重试";
      setErrorMsg(msg);
      setMode("error");
    }
  };

  // ── 方式 B：购买检测套餐（跳转 WebView 订单页）──────────────
  const handleBuyKit = () => {
    // 小程序内嵌 WebView，打开套餐购买 H5 页面
    Taro.navigateTo({
      url: `/pages/webview/index?url=${encodeURIComponent("https://yourdomain.com/order-kit")}`,
    });
  };

  // ── 渲染 ────────────────────────────────────────────────────
  if (mode === "uploading") {
    return (
      <View className="upload-page center">
        <View className="upload-spinner">⏳</View>
        <Text className="upload-status">正在上传并加密存储...</Text>
        <Text className="upload-hint">请勿关闭小程序</Text>
      </View>
    );
  }

  if (mode === "success") {
    return (
      <View className="upload-page center">
        <Text className="success-icon">✅</Text>
        <Text className="success-title">上传成功！</Text>
        <Text className="success-sub">正在启动表观遗传分析（约 5-10 分钟）</Text>
        <Text className="success-note">任务 ID：{jobId}</Text>
      </View>
    );
  }

  if (mode === "error") {
    return (
      <View className="upload-page center">
        <Text className="error-icon">❌</Text>
        <Text className="error-title">上传失败</Text>
        <Text className="error-msg">{errorMsg}</Text>
        <Button className="retry-btn" onClick={() => setMode("select")}>
          重新上传
        </Button>
      </View>
    );
  }

  return (
    <View className="upload-page">
      <Text className="page-title">开始检测</Text>
      <Text className="page-sub">选择您的数据来源</Text>

      {/* 卡片 A：已有检测数据 */}
      <View className="option-card" onClick={handleBetaCsvUpload}>
        <View className="card-icon">📊</View>
        <View className="card-content">
          <Text className="card-title">上传已有数据</Text>
          <Text className="card-desc">
            已从实验室获得 Beta 矩阵 CSV 文件{"\n"}
            支持 EPIC 芯片（850K）及 450K 数组
          </Text>
        </View>
        <Text className="card-arrow">›</Text>
      </View>

      {/* 卡片 B：购买套餐 */}
      <View className="option-card featured" onClick={handleBuyKit}>
        <View className="card-icon">🧪</View>
        <View className="card-content">
          <Text className="card-title">购买检测套餐</Text>
          <Text className="card-desc">
            居家采样，寄回实验室{"\n"}
            约 3 周出结果，自动同步至本平台
          </Text>
          <Text className="card-price">¥ 2,999 起</Text>
        </View>
        <Text className="card-arrow">›</Text>
      </View>

      <Text className="privacy-note">
        🔒 所有数据采用 AES-256-GCM 加密存储{"\n"}
        遗传数据严格遵守《人类遗传资源管理条例》
      </Text>
    </View>
  );
}
