"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { Icon } from "@/components/Icons";
import { CitationTabs } from "@/components/citations/CitationTabs";
import { suggestCitations, type CitationSuggestResponse } from "@/lib/api";

const ACCEPT = ".docx,.md,.markdown,.txt";

export default function CitationSuggestPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<CitationSuggestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const pick = (list: FileList | null) => {
    if (!list || list.length === 0) return;
    setFile(list[0]);
    setResult(null);
    setError("");
  };

  const run = async () => {
    if (!file) {
      setError("请先上传论文文件");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await suggestCitations(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "分析失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const copy = async (key: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      setError("浏览器拒绝了剪贴板访问");
    }
  };

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">首页</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features" className="transition hover:text-brand-600">引用助手</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">引用建议</span>
      </nav>

      <header className="mt-6 flex flex-wrap items-start gap-5">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-500 text-white shadow-lg shadow-violet-500/25">
          <Icon name="book" className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">引用建议</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            上传整篇论文，AI 通读后指出**哪几句是别人的观点、数据或方法却没有标注引用**，并为每处给出可核实的候选文献。
          </p>
        </div>
      </header>

      <CitationTabs active="suggest" />

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            pick(event.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={
            "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-9 text-center transition " +
            (dragging
              ? "border-violet-400 bg-violet-50/60"
              : "border-slate-300 hover:border-violet-300 hover:bg-slate-50")
          }
        >
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-violet-50 text-violet-600">
            <Icon name="book" className="h-5 w-5" />
          </span>
          <p className="mt-3 text-sm font-semibold text-slate-700">
            {file ? file.name : "把论文拖到这里，或点击选择"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            支持 .docx / .md / .txt，单份 10MB。分析约需 20–40 秒
          </p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(event) => {
              pick(event.target.files);
              event.target.value = "";
            }}
          />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={run}
            disabled={loading || !file}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/25 transition hover:-translate-y-0.5 disabled:opacity-50"
          >
            {loading ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                正在通读全文…
              </>
            ) : (
              <>
                <Icon name="sparkles" className="h-4 w-4" />
                开始分析
              </>
            )}
          </button>
          {result && (
            <span className="text-xs text-slate-500">
              扫描 {result.scanned_paragraphs} 段，发现 {result.total} 处需要引用
            </span>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}
      </section>

      {result && result.total === 0 && (
        <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-800">
          没有发现明显缺少引用的地方。可能这篇文稿本身以作者自己的实验为主，
          或者需要引用之处已经标注过了。
        </div>
      )}

      {result && result.spots.length > 0 && (
        <div className="mt-6 space-y-4">
          {result.spots.map((spot, spotIndex) => (
            <section
              key={spotIndex}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                  需要引用 · 第 {spotIndex + 1} 处
                </span>
                <span className="text-xs text-slate-400">检索词：{spot.query}</span>
              </div>

              <blockquote className="mt-3 rounded-xl border-l-4 border-amber-300 bg-amber-50/60 px-4 py-3 text-sm leading-7 text-slate-800">
                {spot.sentence}
              </blockquote>
              <p className="mt-2 text-xs text-slate-500">判断依据：{spot.reason}</p>

              {spot.candidates.length === 0 ? (
                <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
                  没有检索到匹配的文献。可以换个更具体的表述后再试。
                </p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {spot.candidates.map((candidate) => {
                    const key = spotIndex + "-" + candidate.index;
                    return (
                      <li key={key} className="rounded-xl border border-slate-200 p-3">
                        <p className="text-sm leading-6 text-slate-800">{candidate.text}</p>
                        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
                          <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-slate-500">
                            {candidate.venue || "未知来源"}
                          </span>
                          {candidate.year && <span className="text-slate-400">{candidate.year}</span>}
                          {candidate.doi && (
                            <a
                              href={"https://doi.org/" + candidate.doi}
                              target="_blank"
                              rel="noreferrer"
                              className="text-violet-600 underline-offset-2 hover:underline"
                            >
                              DOI
                            </a>
                          )}
                          <button
                            type="button"
                            onClick={() => copy(key, candidate.text)}
                            className="rounded-md border border-slate-300 px-2 py-0.5 text-slate-600 transition hover:border-slate-400"
                          >
                            {copied === key ? "已复制" : "复制引用"}
                          </button>
                          <button
                            type="button"
                            onClick={() => copy(key + "-bib", candidate.bibtex)}
                            className="rounded-md border border-slate-300 px-2 py-0.5 text-slate-600 transition hover:border-slate-400"
                          >
                            {copied === key + "-bib" ? "已复制" : "复制 BibTeX"}
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
