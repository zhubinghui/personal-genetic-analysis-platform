"use client";

import { useState } from "react";
import { Salad, Dumbbell, Pill, Heart, Pin, ChevronRight, ChevronDown } from "lucide-react";
import type { Recommendation } from "@/types";
import InfoTip from "@/components/ui/InfoTip";

const CATEGORY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  diet: Salad,
  exercise: Dumbbell,
  supplement: Pill,
  lifestyle: Heart,
};

const EVIDENCE_COLORS: Record<string, string> = {
  A: "bg-green-100 text-green-700",
  B: "bg-yellow-100 text-yellow-700",
  C: "bg-gray-100 text-gray-600",
};

export default function RecommendationCard({ rec }: { rec: Recommendation }) {
  const [showLiterature, setShowLiterature] = useState(false);
  const hasLiterature = rec.literature_references && rec.literature_references.length > 0;

  return (
    <div className="bg-white rounded-xl border p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {(() => { const Icon = CATEGORY_ICONS[rec.category] ?? Pin; return <Icon className="w-5 h-5 text-brand-600 shrink-0" />; })()}
          <h4 className="font-semibold text-gray-800">{rec.title}</h4>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-medium ${EVIDENCE_COLORS[rec.evidence_level]}`}>
            {rec.evidence_level} 级证据
            <InfoTip term={`evidence_${rec.evidence_level.toLowerCase()}`} />
          </span>
          <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full text-xs">
            {rec.timeframe_weeks} 周
          </span>
        </div>
      </div>

      <p className="text-sm text-gray-600 leading-relaxed">{rec.summary}</p>

      {/* PubMed 引用 */}
      {rec.pubmed_urls.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {rec.pubmed_urls.map((url, i) => (
            <a
              key={i}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-500 hover:underline"
            >
              PMID:{rec.pmids[i]}
            </a>
          ))}
        </div>
      )}

      {/* 知识库文献支撑 */}
      {hasLiterature && (
        <div className="border-t pt-2">
          <button
            onClick={() => setShowLiterature(!showLiterature)}
            className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 hover:text-emerald-700 transition"
          >
            {showLiterature ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            知识库文献支撑（{rec.literature_references.length} 条）
          </button>

          {showLiterature && (
            <div className="mt-2 space-y-2">
              {rec.literature_references.map((ref, i) => (
                <div key={i} className="bg-gray-50 rounded-lg p-3 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium text-gray-800 truncate">
                      {ref.document_title}
                    </span>
                    <div className="flex items-center gap-2 shrink-0">
                      {ref.page_number && (
                        <span className="text-xs text-gray-400">p.{ref.page_number}</span>
                      )}
                      <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded text-xs">
                        {(ref.relevance_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 leading-relaxed line-clamp-3">
                    {ref.excerpt}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
