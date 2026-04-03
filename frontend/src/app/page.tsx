"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Cookies from "js-cookie";
import {
  Dna, Microscope, BarChart3, Shield, Clock, Activity,
  ArrowRight, CheckCircle, Lock, FlaskConical,
} from "lucide-react";

export default function Home() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = Cookies.get("access_token");
    if (token) {
      router.replace("/dashboard");
    } else {
      setChecking(false);
    }
  }, [router]);

  if (checking) return null;

  return (
    <main className="min-h-screen bg-white">
      {/* ── Hero Section ───────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 gradient-brand opacity-60" />
        <div className="absolute top-20 right-10 w-96 h-96 bg-brand-200/20 rounded-full blur-3xl" />
        <div className="absolute bottom-10 left-10 w-72 h-72 bg-brand-300/15 rounded-full blur-3xl" />

        <div className="relative max-w-6xl mx-auto px-6 py-24 md:py-32">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 mb-6">
              <Dna className="w-8 h-8 text-brand-600" />
              <span className="text-sm font-semibold text-brand-600 tracking-wide uppercase">
                Epigenetic Analysis Platform
              </span>
            </div>

            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 leading-tight mb-6">
              精准量化您的
              <span className="text-brand-600">生物学年龄</span>
            </h1>

            <p className="text-lg md:text-xl text-gray-600 leading-relaxed mb-8 max-w-2xl">
              上传血液 DNA 甲基化数据，获取 4 大经同行评审的衰老时钟评估、
              9 大生理系统维度分析，以及基于 PubMed 文献的个性化循证干预建议。
            </p>

            <div className="flex flex-col sm:flex-row gap-4">
              <Link
                href="/register"
                className="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-brand-600 text-white rounded-xl font-semibold hover:bg-brand-700 transition shadow-lg shadow-brand-200/50"
              >
                免费开始分析
                <ArrowRight className="w-5 h-5" />
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center justify-center gap-2 px-8 py-3.5 border-2 border-gray-200 text-gray-700 rounded-xl font-semibold hover:border-brand-300 hover:text-brand-600 transition"
              >
                已有账号，登录
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust Metrics ──────────────────────────────── */}
      <section className="border-y border-gray-100 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { value: "4", label: "衰老时钟模型", sub: "经同行评审" },
              { value: "19", label: "生物学指标", sub: "9 大系统覆盖" },
              { value: "310+", label: "循证推荐条目", sub: "PubMed 文献支撑" },
              { value: "AES-256", label: "加密保护", sub: "隐私优先架构" },
            ].map((item) => (
              <div key={item.label}>
                <p className="text-3xl font-bold text-brand-600 metric-value">{item.value}</p>
                <p className="text-sm font-medium text-gray-800 mt-1">{item.label}</p>
                <p className="text-xs text-gray-400">{item.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features Grid ──────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">科学驱动的衰老评估</h2>
          <p className="text-gray-500 max-w-xl mx-auto">
            整合多维表观遗传分析模型，提供全面、可靠、可操作的抗衰老洞察
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[
            {
              icon: Clock,
              title: "多时钟交叉验证",
              desc: "Horvath、GrimAge、PhenoAge、DunedinPACE 四大时钟并行计算，交叉验证结果可靠性。",
            },
            {
              icon: Activity,
              title: "9 大系统维度拆解",
              desc: "心血管、代谢、免疫、肾脏、肝脏、肺功能、牙周、认知、体能 — 精确定位衰老薄弱环节。",
            },
            {
              icon: FlaskConical,
              title: "循证干预建议",
              desc: "310+ 条基于 GRADE 分级的建议，每条附 PubMed 引用，按证据等级和个人维度排序。",
            },
            {
              icon: BarChart3,
              title: "纵向趋势追踪",
              desc: "多次采样数据自动对比，折线图 + 雷达图直观展示衰老指标的变化趋势和干预效果。",
            },
            {
              icon: Microscope,
              title: "AI 文献助手",
              desc: "基于本地知识库的 RAG 问答，即时获取衰老研究的学术解读，引用来源可追溯。",
            },
            {
              icon: Shield,
              title: "隐私安全架构",
              desc: "AES-256-GCM 加密存储、假名化数据分离、GDPR 合规删除，您的遗传数据始终受保护。",
            },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className="group p-6 rounded-2xl border border-gray-100 hover:border-brand-200 hover:shadow-lg hover:shadow-brand-50 transition-all duration-300"
              >
                <div className="w-11 h-11 rounded-xl bg-brand-50 flex items-center justify-center mb-4 group-hover:bg-brand-100 transition-colors">
                  <Icon className="w-5 h-5 text-brand-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── How It Works ───────────────────────────────── */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-gray-900 mb-3">三步获取分析报告</h2>
            <p className="text-gray-500">从上传数据到获得个性化报告，简单快捷</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                title: "上传数据",
                desc: "上传 Illumina IDAT 文件对或预处理 Beta 值矩阵 CSV，支持 EPIC 和 450K 芯片。",
              },
              {
                step: "02",
                title: "自动分析",
                desc: "平台自动完成质控、归一化，并行运行 4 个衰老时钟，计算 19 项生物学指标。",
              },
              {
                step: "03",
                title: "查看报告",
                desc: "交互式报告含时钟对比、维度雷达图、同龄人群对标、个性化循证建议和 PDF 下载。",
              },
            ].map((item) => (
              <div key={item.step} className="relative">
                <span className="text-6xl font-black text-brand-100">{item.step}</span>
                <h3 className="text-lg font-semibold text-gray-900 mt-2 mb-2">{item.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Science Credibility ─────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="bg-brand-50 rounded-3xl p-8 md:p-12">
          <div className="flex flex-col md:flex-row items-start gap-8">
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">基于同行评审的科学模型</h2>
              <p className="text-gray-600 leading-relaxed mb-6">
                本平台使用的衰老时钟均来自国际顶级期刊发表的研究成果，涵盖不同维度的衰老量化方法。
              </p>
              <div className="space-y-3">
                {[
                  "Horvath (2013) — 多组织 DNA 甲基化年龄",
                  "GrimAge (Lu et al. 2019) — 死亡率相关衰老指标",
                  "PhenoAge (Levine et al. 2018) — 临床表型衰老时钟",
                  "DunedinPACE (Belsky et al. 2022) — 衰老速率量化",
                ].map((item) => (
                  <div key={item} className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-brand-600 mt-0.5 shrink-0" />
                    <span className="text-sm text-gray-700">{item}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-3 shrink-0">
              <div className="bg-white rounded-xl p-4 text-center shadow-sm">
                <Lock className="w-6 h-6 text-brand-600 mx-auto mb-2" />
                <p className="text-xs text-gray-500">AES-256-GCM</p>
                <p className="text-xs font-semibold text-gray-700">端到端加密</p>
              </div>
              <div className="bg-white rounded-xl p-4 text-center shadow-sm">
                <Shield className="w-6 h-6 text-brand-600 mx-auto mb-2" />
                <p className="text-xs text-gray-500">假名化隔离</p>
                <p className="text-xs font-semibold text-gray-700">GDPR 合规</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA Section ────────────────────────────────── */}
      <section className="border-t border-gray-100 bg-white py-20">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">开始量化您的衰老速率</h2>
          <p className="text-gray-500 mb-8">
            免费注册，上传您的 DNA 甲基化数据，5-20 分钟内获取完整报告
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-10 py-4 bg-brand-600 text-white rounded-xl font-semibold text-lg hover:bg-brand-700 transition shadow-lg shadow-brand-200/50"
          >
            免费开始分析
            <ArrowRight className="w-5 h-5" />
          </Link>
          <p className="text-xs text-gray-400 mt-6">
            本平台仅提供健康管理参考，不构成医疗诊断建议。所有数据使用 AES-256 加密保护。
          </p>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────── */}
      <footer className="border-t border-gray-100 py-8">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Dna className="w-5 h-5 text-brand-600" />
            <span className="text-sm font-semibold text-gray-700">基因抗衰老分析平台</span>
          </div>
          <p className="text-xs text-gray-400">
            Powered by Horvath · GrimAge · PhenoAge · DunedinPACE
          </p>
        </div>
      </footer>
    </main>
  );
}
