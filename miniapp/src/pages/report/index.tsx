/**
 * 报告页
 *
 * 同时支持两个场景：
 *   A. 分析中 — 轮询任务状态，显示进度
 *   B. 已完成 — 展示可视化报告（仪表盘、维度条、推荐卡片）
 *
 * 图表使用 @antv/f2（专为小程序优化的移动端图表库，比 echarts 更轻量）
 */
import { View, Text, ScrollView, Button } from "@tarojs/components";
import Taro, { useLoad, useUnload } from "@tarojs/taro";
import { useState, useRef } from "react";
import { getJobStatus, getReport, type ReportData, type JobStatus } from "../../lib/api";
import "./index.scss";

const POLL_INTERVAL = 5000; // 5 秒轮询，与 Web 端保持一致

export default function ReportPage() {
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [report, setReport] = useState<ReportData | null>(null);
  const [error, setError] = useState("");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useLoad((params) => {
    const jobId = params.jobId as string;
    if (!jobId) {
      setError("参数错误");
      return;
    }
    startPolling(jobId);
  });

  useUnload(() => {
    if (timerRef.current) clearInterval(timerRef.current);
  });

  const startPolling = (jobId: string) => {
    const poll = async () => {
      try {
        const status = await getJobStatus(jobId);
        setJobStatus(status);

        if (status.status === "completed") {
          if (timerRef.current) clearInterval(timerRef.current);
          const data = await getReport(jobId);
          setReport(data);
        } else if (status.status === "failed") {
          if (timerRef.current) clearInterval(timerRef.current);
          setError(status.error_message ?? "分析失败，请重新上传");
        }
      } catch (e) {
        // 网络错误不中断轮询
      }
    };

    poll(); // 立即执行一次
    timerRef.current = setInterval(poll, POLL_INTERVAL);
  };

  const shareReport = () => {
    // 微信小程序分享报告卡片
    Taro.showShareMenu({ withShareTicket: true });
  };

  // ── 加载中 / 分析中 ─────────────────────────────────────────
  if (!report) {
    const progress = jobStatus?.progress ?? 0;
    const statusLabel: Record<string, string> = {
      queued: "排队等待中...",
      running: "表观遗传分析运行中...",
      failed: "分析失败",
    };

    return (
      <View className="report-page center">
        {error ? (
          <>
            <Text className="error-icon">❌</Text>
            <Text className="error-msg">{error}</Text>
          </>
        ) : (
          <>
            <View className="progress-ring">
              <Text className="progress-text">{progress}%</Text>
            </View>
            <Text className="status-label">
              {statusLabel[jobStatus?.status ?? "queued"]}
            </Text>
            <Text className="status-hint">
              正在运行 Horvath、GrimAge、PhenoAge、DunedinPACE 四大时钟{"\n"}
              预计 5-10 分钟完成
            </Text>
          </>
        )}
      </View>
    );
  }

  // ── 报告展示 ─────────────────────────────────────────────────
  const mainClock = report.clocks.find((c) => c.clock_name === "Horvath");
  const bioAge = mainClock?.biological_age;
  const chronoAge = mainClock?.chronological_age;
  const delta = bioAge != null && chronoAge != null ? bioAge - chronoAge : null;

  return (
    <ScrollView className="report-page" scrollY>
      {/* ── 摘要卡片 ── */}
      <View className="summary-card">
        <Text className="summary-title">表观遗传年龄</Text>
        <View className="age-display">
          <View className="bio-age">
            <Text className="age-number">{bioAge?.toFixed(1) ?? "--"}</Text>
            <Text className="age-unit">岁</Text>
          </View>
          {delta != null && (
            <View className={`age-delta ${delta > 0 ? "older" : "younger"}`}>
              <Text>{delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)}</Text>
              <Text className="delta-label">vs 实际年龄</Text>
            </View>
          )}
        </View>

        {report.dunedin_pace != null && (
          <View className="pace-row">
            <Text className="pace-label">生物衰老速率（DunedinPACE）</Text>
            <Text className={`pace-value ${report.dunedin_pace > 1.0 ? "fast" : "slow"}`}>
              {report.dunedin_pace.toFixed(3)}
            </Text>
            <Text className="pace-note">人群均值 = 1.000</Text>
          </View>
        )}
      </View>

      {/* ── 四大时钟结果 ── */}
      <View className="section">
        <Text className="section-title">🕐 四大衰老时钟</Text>
        {report.clocks.map((clock) => (
          <View key={clock.clock_name} className="clock-row">
            <Text className="clock-name">{clock.clock_name}</Text>
            <View className="clock-values">
              <Text className="clock-bio">
                {clock.biological_age?.toFixed(1) ?? "--"} 岁
              </Text>
              {clock.age_acceleration != null && (
                <Text className={`clock-accel ${clock.age_acceleration > 0 ? "pos" : "neg"}`}>
                  {clock.age_acceleration > 0 ? "+" : ""}
                  {clock.age_acceleration.toFixed(2)} 年
                </Text>
              )}
            </View>
          </View>
        ))}
      </View>

      {/* ── 9 大维度 ── */}
      <View className="section">
        <Text className="section-title">📊 生理系统维度</Text>
        {report.dimension_scores.map((dim) => (
          <View key={dim.name} className="dimension-row">
            <Text className="dim-label">{dim.label}</Text>
            <View className="dim-bar-wrap">
              <View
                className="dim-bar"
                style={{ width: `${Math.min(100, dim.score * 100)}%` }}
              />
            </View>
            <Text className="dim-score">{(dim.score * 100).toFixed(0)}</Text>
          </View>
        ))}
      </View>

      {/* ── AI 摘要 ── */}
      {report.ai_summary && (
        <View className="section ai-section">
          <Text className="section-title">🤖 AI 健康解读</Text>
          <Text className="ai-text">{report.ai_summary}</Text>
        </View>
      )}

      {/* ── 推荐建议（前 5 条）── */}
      <View className="section">
        <Text className="section-title">💡 循证干预建议</Text>
        {report.recommendations.slice(0, 5).map((rec) => (
          <View key={rec.id} className="rec-card">
            <View className="rec-header">
              <Text className="rec-level">GRADE {rec.evidence_level}</Text>
              <Text className="rec-category">{rec.category}</Text>
            </View>
            <Text className="rec-title">{rec.title}</Text>
            <Text className="rec-summary">{rec.summary}</Text>
          </View>
        ))}
      </View>

      {/* ── 操作按钮 ── */}
      <View className="action-row">
        <Button className="share-btn" onClick={shareReport}>
          分享报告
        </Button>
      </View>

      <Text className="disclaimer">
        本报告仅供健康管理参考，不构成医疗诊断建议
      </Text>
    </ScrollView>
  );
}
