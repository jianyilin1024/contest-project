"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";

import { Icon } from "@/components/Icons";
import { MarkdownPreview } from "@/components/MarkdownPreview";
import { ModeTabs } from "@/components/merge/ModeTabs";
import { analyzeMerge, exportMerge, type MergeResponse } from "@/lib/api";

const ACCEPT = ".docx,.md,.markdown,.txt";
const MAX_FILES = 20;

type Entry = {
  id: string;
  file: File;
  author: string;
  title: string;
};

function stem(filename: string): string {
  return filename.replace(/\.[^.]+$/, "");
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function MergePage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [docTitle, setDocTitle] = useState("小组作业合并稿");
  const [result, setResult] = useState<MergeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const addFiles = useCallback((fileList: FileList | null) => {
    if (!fileList) return;
    const incoming = Array.from(fileList);
    setEntries((prev) => {
      const room = MAX_FILES - prev.length;
      const accepted = incoming.slice(0, Math.max(0, room));
      return [
        ...prev,
        ...accepted.map((file) => ({
          id: `${file.name}-${file.size}-${Math.random().toString(36).slice(2, 8)}`,
          file,
          author: "",
          title: stem(file.name),
        })),
      ];
    });
    setResult(null);
    setError("");
  }, []);

  const updateEntry = (id: string, patch: Partial<Entry>) => {
    setEntries((prev) => prev.map((entry) => (entry.id === id ? { ...entry, ...patch } : entry)));
  };

  const removeEntry = (id: string) => {
    setEntries((prev) => prev.filter((entry) => entry.id !== id));
    setResult(null);
  };

  const run = async () => {
    if (entries.length === 0) {
      setError("请先添加至少一份文稿");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const meta = entries.map((entry) => ({ author: entry.author, title: entry.title }));
      const data = await analyzeMerge(
        entries.map((entry) => entry.file),
        meta,
        docTitle || "合并文稿",
      );
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "整合失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const download = async (format: "md" | "docx") => {
    if (!result) return;
    try {
      const blob = await exportMerge(result.markdown, docTitle || "合并文稿", format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${docTitle || "合并文稿"}.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    }
  };

  const copy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("浏览器拒绝了剪贴板访问，请手动选择复制");
    }
  };

  return (
    <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">首页</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features" className="transition hover:text-brand-600">功能分区</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">多部分整合</span>
      </nav>

      <ModeTabs active="multi" />

      <header className="mt-8 flex flex-wrap items-start gap-5">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-500 text-white shadow-lg shadow-indigo-500/25">
          <Icon name="layers" className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-900/5 px-2 py-0.5 text-xs font-bold text-slate-500">F1</span>
            <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">可用</span>
          </div>
          <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">多部分整合</h1>
          <p className="mt-2 text-sm text-slate-500">
            上传各成员负责的文稿，自动归一标题层级与编号，并给出重复内容与术语不一致的核对提示。
          </p>
        </div>
      </header>

      {/* ================= 上传区 ================= */}
      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            addFiles(event.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragging
              ? "border-indigo-400 bg-indigo-50/60"
              : "border-slate-300 hover:border-indigo-300 hover:bg-slate-50"
          }`}
        >
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
            <Icon name="layers" className="h-5 w-5" />
          </span>
          <p className="mt-4 text-sm font-semibold text-slate-700">
            把文稿拖到这里，或点击选择文件
          </p>
          <p className="mt-1.5 text-xs text-slate-500">
            支持 .docx / .md / .txt，可一次选多份，最多 {MAX_FILES} 份、单份 10MB
          </p>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPT}
            className="hidden"
            onChange={(event) => {
              addFiles(event.target.files);
              event.target.value = "";
            }}
          />
        </div>

        {entries.length > 0 && (
          <ul className="mt-5 space-y-3">
            {entries.map((entry, index) => (
              <li
                key={entry.id}
                className="rounded-xl border border-slate-200 bg-slate-50/60 p-4"
              >
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white text-xs font-bold text-slate-500 shadow-sm">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800">{entry.file.name}</p>
                    <p className="mt-0.5 text-xs text-slate-400">{formatSize(entry.file.size)}</p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <label className="block">
                        <span className="text-xs font-medium text-slate-500">作者</span>
                        <input
                          value={entry.author}
                          onChange={(event) => updateEntry(entry.id, { author: event.target.value })}
                          placeholder="如：张三"
                          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs font-medium text-slate-500">章节名（留空则用文稿内第一个标题）</span>
                        <input
                          value={entry.title}
                          onChange={(event) => updateEntry(entry.id, { title: event.target.value })}
                          placeholder="如：第一章 绪论"
                          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                        />
                      </label>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeEntry(entry.id)}
                    className="rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
                  >
                    移除
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-5 flex flex-wrap items-end gap-4 border-t border-slate-100 pt-5">
          <label className="block">
            <span className="text-xs font-medium text-slate-500">合并稿标题</span>
            <input
              value={docTitle}
              onChange={(event) => setDocTitle(event.target.value)}
              className="mt-1 w-64 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
            />
          </label>
          <button
            type="button"
            onClick={run}
            disabled={loading || entries.length === 0}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {loading ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                正在整合…
              </>
            ) : (
              <>
                <Icon name="sparkles" className="h-4 w-4" />
                开始整合
              </>
            )}
          </button>
          {entries.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setEntries([]);
                setResult(null);
                setError("");
              }}
              className="text-sm text-slate-500 transition hover:text-slate-800"
            >
              清空
            </button>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}
      </section>

      {result && (
        <MergeResult
          result={result}
          onDownload={download}
          onCopy={copy}
          copied={copied}
          onFormat={() => {
            window.sessionStorage.setItem("format:markdown", result.markdown);
            router.push("/features/format");
          }}
        />
      )}
    </main>
  );
}

/* ==================== 结果区 ==================== */

function MergeResult({
  result,
  onDownload,
  onCopy,
  copied,
  onFormat,
}: {
  result: MergeResponse;
  onDownload: (format: "md" | "docx") => void;
  onCopy: () => void;
  copied: boolean;
  onFormat: () => void;
}) {
  const { stats } = result;
  const cards = [
    { label: "文稿", value: stats.documents, tone: "text-slate-900" },
    { label: "章节", value: stats.sections, tone: "text-slate-900" },
    { label: "总字数", value: stats.characters, tone: "text-slate-900" },
    { label: "重复内容", value: stats.duplicates, tone: stats.duplicates ? "text-amber-600" : "text-slate-900" },
    { label: "术语不一致", value: stats.term_conflicts, tone: stats.term_conflicts ? "text-amber-600" : "text-slate-900" },
  ];

  return (
    <div className="mt-8 space-y-6">
      {/* 统计 */}
      <section className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        {cards.map((card) => (
          <div key={card.label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className={`text-2xl font-extrabold ${card.tone}`}>{card.value}</p>
            <p className="mt-0.5 text-xs text-slate-500">{card.label}</p>
          </div>
        ))}
      </section>

      {result.warnings.length > 0 && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <h2 className="flex items-center gap-2 text-sm font-bold text-amber-800">
            <Icon name="info" className="h-4 w-4" />
            提示
          </h2>
          <ul className="mt-2 space-y-1 text-sm text-amber-800">
            {result.warnings.map((warning) => (
              <li key={warning}>· {warning}</li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 目录 */}
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-bold text-slate-800">归一后的目录</h2>
          <p className="mt-1 text-xs text-slate-500">标题层级与编号已统一，缩进表示层级。</p>
          <ul className="mt-4 space-y-1">
            {result.outline.map((node, index) => (
              <li
                key={`${node.number}-${index}`}
                style={{ paddingLeft: `${(node.level - 1) * 16}px` }}
                className="flex items-baseline gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-50"
              >
                <span className="shrink-0 font-mono text-xs font-semibold text-indigo-600">{node.number}</span>
                <span className="min-w-0 flex-1 truncate font-medium text-slate-800">{node.title}</span>
                <span className="shrink-0 text-xs text-slate-400">{node.characters} 字</span>
              </li>
            ))}
          </ul>
        </section>

        {/* 冲突报告 */}
        <section className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-800">
              重复内容
              <span className="ml-2 rounded-md bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-500">
                {result.duplicates.length} 处
              </span>
            </h2>
            {result.duplicates.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">没有发现重复段落。</p>
            ) : (
              <ul className="mt-4 space-y-3">
                {result.duplicates.map((item, index) => (
                  <li key={index} className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                    <p className="text-sm leading-6 text-slate-700">{item.text}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {item.cross_document && (
                        <span className="rounded-md bg-amber-100 px-1.5 py-0.5 text-[11px] font-medium text-amber-700">
                          跨文稿
                        </span>
                      )}
                      {item.occurrences.map((occurrence, occIndex) => (
                        <span key={occIndex} className="text-xs text-slate-500">
                          {occurrence.author || occurrence.source} · {occurrence.section}
                        </span>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-800">
              疑似术语不一致
              <span className="ml-2 rounded-md bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-500">
                {result.terms.length} 处
              </span>
            </h2>
            {result.terms.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">没有发现术语写法差异。</p>
            ) : (
              <ul className="mt-4 space-y-3">
                {result.terms.map((term, index) => (
                  <li key={index} className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <span className="rounded-md bg-white px-2 py-0.5 font-medium text-slate-700 shadow-sm">
                        {term.short}
                      </span>
                      <span className="text-xs text-slate-400">vs</span>
                      <span className="rounded-md bg-white px-2 py-0.5 font-medium text-slate-700 shadow-sm">
                        {term.long}
                      </span>
                    </div>
                    <div className="mt-2 space-y-0.5 text-xs text-slate-500">
                      <p>「{term.short}」出现在：{term.short_docs.join("、")}</p>
                      <p>「{term.long}」出现在：{term.long_docs.join("、")}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-xs text-slate-400">
              启发式检测，只做提示；是否统一由你决定。
            </p>
          </div>
        </section>
      </div>

      {/* 合并稿 */}
      <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-bold text-slate-800">合并稿预览</h2>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onCopy}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-400"
            >
              <Icon name="check" className="h-3.5 w-3.5" />
              {copied ? "已复制" : "复制 Markdown"}
            </button>
            <button
              type="button"
              onClick={() => onDownload("md")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-400"
            >
              下载 .md
            </button>
            <button
              type="button"
              onClick={() => onDownload("docx")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-400"
            >
              快速导出 .docx
            </button>
            <button
              type="button"
              onClick={onFormat}
              className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-sky-600 to-cyan-600 px-3 py-1.5 text-xs font-medium text-white transition hover:from-sky-500 hover:to-cyan-500"
            >
              <Icon name="layout" className="h-3.5 w-3.5" />
              去排版
            </button>
          </div>
        </div>
        <div className="max-h-[32rem] overflow-y-auto px-6 py-5">
          <MarkdownPreview markdown={result.markdown} />
        </div>
      </section>
    </div>
  );
}
