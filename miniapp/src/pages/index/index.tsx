/**
 * 首页
 *
 * 核心逻辑：
 *  - 未登录 → 引导登录
 *  - 已登录，无历史记录 → 引导上传
 *  - 已登录，有历史记录 → 展示最新报告卡片 + 历史列表
 */
import { View, Text, Button } from "@tarojs/components";
import Taro, { useLoad, useDidShow } from "@tarojs/taro";
import { useState } from "react";
import { getSamples, getMe, TokenStore, ApiError } from "../../lib/api";
import "./index.scss";

interface Sample {
  id: string;
  filename: string;
  created_at: string;
  latest_job_id?: string;
}

export default function IndexPage() {
  const [user, setUser] = useState<{ email: string; avatar_url: string | null } | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [loading, setLoading] = useState(true);

  // useDidShow 每次切换到此 Tab 时触发，保证数据最新
  useDidShow(() => {
    loadData();
  });

  const loadData = async () => {
    if (!TokenStore.get()) {
      Taro.redirectTo({ url: "/pages/login/index" });
      return;
    }
    try {
      setLoading(true);
      const [me, { samples: sampleList }] = await Promise.all([getMe(), getSamples()]);
      setUser(me);
      setSamples(sampleList as Sample[]);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        TokenStore.clear();
        Taro.redirectTo({ url: "/pages/login/index" });
      }
    } finally {
      setLoading(false);
    }
  };

  const goUpload = () => Taro.switchTab({ url: "/pages/upload/index" });

  const viewReport = (jobId: string) => {
    Taro.navigateTo({ url: `/pages/report/index?jobId=${jobId}` });
  };

  if (loading) {
    return (
      <View className="index-page center">
        <Text>加载中...</Text>
      </View>
    );
  }

  return (
    <View className="index-page">
      {/* 头部问候 */}
      <View className="greeting-bar">
        <View>
          <Text className="greeting-text">你好 👋</Text>
          <Text className="greeting-sub">{user?.email?.split("@")[0]}</Text>
        </View>
      </View>

      {/* 空状态 */}
      {samples.length === 0 ? (
        <View className="empty-state">
          <Text className="empty-icon">🧬</Text>
          <Text className="empty-title">开始您的第一次检测</Text>
          <Text className="empty-desc">
            上传甲基化芯片数据，或购买检测套餐{"\n"}
            获取个性化的表观遗传衰老分析报告
          </Text>
          <Button className="primary-btn" onClick={goUpload}>
            立即开始
          </Button>
        </View>
      ) : (
        <View className="sample-list">
          <Text className="list-title">检测历史</Text>
          {samples.map((s) => (
            <View
              key={s.id}
              className="sample-card"
              onClick={() => s.latest_job_id && viewReport(s.latest_job_id)}
            >
              <View className="sample-info">
                <Text className="sample-filename">{s.filename}</Text>
                <Text className="sample-date">
                  {new Date(s.created_at).toLocaleDateString("zh-CN")}
                </Text>
              </View>
              <Text className="sample-arrow">›</Text>
            </View>
          ))}
          <Button className="secondary-btn" onClick={goUpload}>
            + 新建检测
          </Button>
        </View>
      )}
    </View>
  );
}
