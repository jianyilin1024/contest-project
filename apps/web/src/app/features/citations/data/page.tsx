"use client";

import Link from "next/link";
import { useState } from "react";

import { Icon } from "@/components/Icons";
import { CitationTabs } from "@/components/citations/CitationTabs";
import { assistData, type DataAssistResponse } from "@/lib/api";

const SAMPLE =
  "本文提出的方法在图像分类任务上取得了显著效果，相比基线方法有明显提升，并且推理速度更快，模型参数量也更小，非常适合部署到移动端设备。";

export default function DataPage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<DataAssistResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState<number | null>(null);

  const run = async () => {
    if (text.trim().length < 10) {
      setError("请粘贴一段需要补充数据的文字（至少 10 字）");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await assistData(text.trim());
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "检索失败");
    } finally {
      setLoading(false);
    }
  };

  const copy = async (index: number, value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(index);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      setError("浏览器拒绝了剪贴板访问");
    }
  };

  return (
    <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">首页</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features" className="transition hover:text-brand-600">引用助手</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">数据补全</span>
      </nav>

      <header className="mt-6 flex flex-wrap items-start gap-5">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-rose-500 to-pink-500 text-white shadow-lg shadow-rose-500/25">
          <Icon name="database" className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">数据补全</h1>
          <p className="mt-2 text-sm text-slate-500">
            找出段落里「该有数据却没有数据」的地方，联网检索后给出带来源链接与原文引用的补充建议。找不到就说找不到，不会编造。
          </p>
        </div>
      </header>

      <CitationTabs active="data" />

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-bold text-slate-800">待补充数据的段落</h2>
          <button
            type="button"
            onClick={() => setText(SAMPLE)}
            className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs text-slate-600 transition hover:border-slate-400"
          >
            填入示例
          </button>
        </div>
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={4}
          placeholder="粘贴一段需要数据支撑的文字…"
          className="mt-3 w-full resize-y rounded-xl border border-slate-300 bg-slate-50/50 p-4 text-sm leading-7 text-slate-700 outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100"
        />
        <div className="mt-3 flex items-center gap-4">
          <button
            type="button"
            onClick={run}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-rose-500 to-pink-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-rose-500/25 transition hover:-translate-y-0.5 disabled:opacity-50"
          >
            {loading ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                正在检索（约 30–40 秒）…
              </>
            ) : (
              <>
                <Icon name="sparkles" className="h-4 w-4" />
                查找数据
              </>
            )}
          </button>
        </div>
        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
        )}
      </section>

      {result && (
        <div className="mt-6 space-y-5">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-800">
              识别到的数据缺口
              <span className="ml-2 rounded-md bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-500">
                {result.gaps.length} 处
              </span>
            </h2>
            {result.gaps.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">这段话的数据已经比较充分，没有发现明显缺口。</p>
            ) : (
              <ul className="mt-3 space-y-2">
                {result.gaps.map((gap, index) => (
                  <li key={index} className="rounded-xl border border-slate-200 p-3">
                    <p className="text-sm leading-6 text-slate-700">{gap.description}</p>
                    <p className="mt-1 text-xs text-slate-400">检索词：{gap.query}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-bold text-slate-800">
                可核实的数据建议
                <span className="ml-2 rounded-md bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-700">
                  {result.suggestions.length} 条
                </span>
              </h2>
              <span className="text-xs text-slate-400">共检索 {result.searched} 个网页</span>
            </div>

            {result.suggestions.length === 0 ? (
              <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                这次没有找到可靠的数据来源。这是预期行为——宁可返回空，也不编造数字。
                <br />
                可以换个说法（写清指标名，如「Top-1 准确率」），或稍后重试。
              </div>
            ) : (
              <ul className="mt-3 space-y-3">
                {result.suggestions.map((item, index) => (
                  <li key={index} className="rounded-xl border border-slate-200 p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-900">{item.value}</p>
                      <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-500">
                        置信度 {Math.round(item.confidence * 100)}%
                      </span>
                    </div>
                    {item.context && (
                      <p className="mt-1 text-xs leading-5 text-slate-500">可用于：{item.context}</p>
                    )}
                    {item.quote && (
                      <blockquote className="mt-2 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
                        原文引用：{item.quote}
                      </blockquote>
                    )}
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-rose-600 underline-offset-2 hover:underline"
                      >
                        {item.source_title || "查看来源"}
                      </a>
                      <button
                        type="button"
                        onClick={() => copy(index, item.value)}
                        className="rounded-md border border-slate-300 px-2 py-0.5 text-slate-600 transition hover:border-slate-400"
                      >
                        {copied === index ? "已复制" : "复制数据"}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </main>
  );
}