"use client";

import { useState, useRef, useEffect } from "react";
import { Dna, Microscope, X, MessageCircle, Send } from "lucide-react";
import { chatApi, ApiError } from "@/lib/api";
import type { ChatSource } from "@/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
}

export default function ChatBot({ jobId }: { jobId?: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const query = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);

    try {
      const res = await chatApi.send(query, jobId);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer, sources: res.sources }]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: e instanceof ApiError ? `抱歉：${e.message}` : "请求失败，请重试" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* 悬浮按钮 */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-brand-600 text-white rounded-full
                   shadow-lg shadow-brand-200 hover:bg-brand-700 transition-all z-50
                   flex items-center justify-center text-2xl"
        title="AI 助手"
      >
        {open ? <X className="w-6 h-6" /> : <MessageCircle className="w-6 h-6" />}
      </button>

      {/* 对话面板 */}
      {open && (
        <div className="fixed bottom-24 right-6 w-96 h-[32rem] bg-white dark:bg-gray-900 rounded-2xl
                        shadow-2xl border border-gray-200 dark:border-gray-700 flex flex-col z-50 overflow-hidden">
          {/* 头部 */}
          <div className="px-4 py-3 bg-brand-600 text-white flex items-center gap-2">
            <Dna className="w-5 h-5" />
            <div>
              <p className="font-semibold text-sm">AI 衰老研究助手</p>
              <p className="text-xs text-brand-100">基于知识库文献为您解答</p>
            </div>
          </div>

          {/* 消息列表 */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.length === 0 && (
              <div className="text-center text-gray-400 text-sm py-8 space-y-2">
                <Microscope className="w-8 h-8 text-gray-300" />
                <p>您好！我可以基于学术文献为您解答衰老相关问题。</p>
                <div className="space-y-1 pt-2">
                  {["DunedinPACE 高于 1.0 意味着什么？", "如何通过饮食减缓表观遗传衰老？", "Horvath 时钟的原理是什么？"].map((q) => (
                    <button
                      key={q}
                      onClick={() => { setInput(q); }}
                      className="block w-full text-left text-xs px-3 py-1.5 bg-gray-50 dark:bg-gray-800
                                 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-brand-50 transition"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-brand-600 text-white rounded-br-sm"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-bl-sm"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-200/30 space-y-0.5">
                      <p className="text-xs opacity-60">引用来源：</p>
                      {msg.sources.map((s, j) => (
                        <p key={j} className="text-xs opacity-50">
                          [{s.document_title}] {s.page_number ? `p.${s.page_number}` : ""} ({(s.relevance_score * 100).toFixed(0)}%)
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 dark:bg-gray-800 rounded-xl px-4 py-2 text-sm text-gray-500">
                  <span className="animate-pulse">思考中...</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* 输入区 */}
          <div className="px-3 py-2 border-t border-gray-100 dark:border-gray-800">
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
                placeholder="输入问题..."
                className="flex-1 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-sm
                           bg-gray-50 dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
                disabled={loading}
              />
              <button
                onClick={send}
                disabled={loading || !input.trim()}
                className="px-3 py-2 bg-brand-600 text-white rounded-xl text-sm
                           hover:bg-brand-700 disabled:opacity-50 transition"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
