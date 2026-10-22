"use client";

import Link from "next/link";
import { useState } from "react";

import { Icon } from "@/components/Icons";
import { searchReferences, type CitationEntry } from "@/lib/api";

const EXAMPLES = ["few-shot image classification", "大语言模型 幻觉 检测", "graph neural network recommendation"];

export default function ReferencesPage() {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(8);
  const [entries, setEntries] = useState<CitationEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const run = async () => {
    if (!query.trim()) {
      setError("请输入检索关键词");
      return;
    }
    setLoading(true);
    setError("");
    setEntries([]);
    try {
      const data = await searchReferences(query.trim(), limit);
      setEntries(data.entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : "检索失败");
    } finally {
      setLoading(false);
    }
  };

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(entries.map((entry) => entry.text).join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("浏览器拒绝了剪贴板访问");
    }
  };

  return (
    <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">首页</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features" className="transition hover:text-brand-600">功能分区</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">参考文献助手</span>
      </nav>

      <header className="mt-6 flex flex-wrap items-start gap-5">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-500 text-white shadow-lg shadow-violet-500/25">
          <Icon name="book" className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-900/5 px-2 py-0.5 text-xs font-bold text-slate-500">F7</span>
            <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">可用</span>
          </div>
          <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">参考文献助手</h1>
          <p className="mt-2 text-sm text-slate-500">
            从 OpenAlex 与 Crossref 检索**真实存在**的文献，本地按 GB/T 7714-2015 格式化。不生成、不编造。
          </p>
        </div>
      </header>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <label className="block flex-1">
            <span className="text-xs font-medium text-slate-500">检索关键词（英文召回更好）</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void run();
              }}
              placeholder="如：few-shot image classification"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-500">条数</span>
            <select
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value))}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-violet-400"
            >
              {[5, 8, 10, 15, 20].map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={run}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/25 transition hover:-translate-y-0.5 disabled:opacity-50"
          >
            {loading ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                检索中…
              </>
            ) : (
              <>
                <Icon name="sparkles" className="h-4 w-4" />
                检索文献
              </>
            )}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setQuery(example)}
              className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-500 transition hover:border-violet-300 hover:text-violet-700"
            >
              {example}
            </button>
          ))}
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
        )}
      </section>

      {entries.length > 0 && (
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-bold text-slate-800">检索结果（{entries.length} 条）</h2>
            <button
              type="button"
              onClick={copyAll}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-400"
            >
              {copied ? "已复制" : "复制全部"}
            </button>
          </div>
          <ul className="mt-3 space-y-2">
            {entries.map((entry) => (
              <li key={entry.index} className="rounded-xl border border-slate-200 p-3">
                <p className="text-sm leading-6 text-slate-800">{entry.text}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                  <span className="rounded-md bg-slate-100 px-1.5 py-0.5">{entry.record.kind}</span>
                  <span>被引 {entry.record.cited_by}</span>
                  <span>{entry.record.source}</span>
                  {entry.record.doi && (
                    <a
                      href={`https://doi.org/${entry.record.doi}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-violet-600 underline-offset-2 hover:underline"
                    >
                      DOI
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-400">
            条目来自 OpenAlex / Crossref 的真实元数据；格式按 GB/T 7714-2015 在本地生成。
          </p>
        </section>
      )}
    </main>
  );
}
