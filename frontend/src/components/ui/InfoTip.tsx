"use client";

import { GLOSSARY } from "@/lib/glossary";

/**
 * 术语提示组件 — 在文本旁显示 ? 图标，悬停时弹出解释
 *
 * 用法 1（按词典 key）：<InfoTip term="horvath" />
 * 用法 2（自定义文本）：<InfoTip tip="这是自定义提示" />
 * 用法 3（行内标签）：<InfoTip term="horvath" inline />
 */
export default function InfoTip({
  term,
  tip,
  inline = false,
}: {
  term?: string;
  tip?: string;
  inline?: boolean;
}) {
  const entry = term ? GLOSSARY[term] : null;
  const tooltipText = tip || entry?.tip;

  if (!tooltipText) return null;

  return (
    <span className="info-tip-wrapper">
      <span className="info-tip-trigger" aria-label={tooltipText}>
        ?
      </span>
      <span className="info-tip-content">
        {entry?.label && <strong className="info-tip-title">{entry.label}</strong>}
        {tooltipText}
      </span>
    </span>
  );
}

/**
 * 带标签的术语提示 — 将标签文字和 ? 图标组合在一起
 *
 * 用法：<TermLabel term="horvath">Horvath 生物学年龄</TermLabel>
 */
export function TermLabel({
  term,
  tip,
  children,
  className = "",
}: {
  term?: string;
  tip?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-0.5 ${className}`}>
      {children}
      <InfoTip term={term} tip={tip} />
    </span>
  );
}
