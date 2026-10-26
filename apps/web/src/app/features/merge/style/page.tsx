"use client";

import Link from "next/link";
import { useState } from "react";

import { Icon } from "@/components/Icons";
import { ModeTabs } from "@/components/merge/ModeTabs";
import { MarkdownPreview } from "@/components/MarkdownPreview";
import {
  assembleRewrite,
  renderDocx,
  rewriteStyle,
  type RewriteSegment,
} from "@/lib/api";

const SAMPLE = [
  "# 第二章 研究方法",
  "",
  "我们觉得吧，这个元学习框架其实挺适合小样本场景的，因为它能学到一个比较好的初始化。",
  "",
  "本文采用元学习框架，构建了基于任务采样的训练流程，并在每个任务内进行五次梯度更新。",
  "",
  "实验这块儿我们跑了好多组，效果都还不错，基本上比 baseline 强一些。",
].join("\n");

/**
 * 用语风格统一：逐段改写 + 左右对照 + 逐句接受。
 *
 * 默认只勾选真正改动的段落，未改动的段不占用户决策精力。
 */
export default function StylePage() {
  const [markdown, setMarkdown] = useState("");
  const [segments, setSegments] = useState<RewriteSegment[]>([]);
  const [accepted, setAccepted] = useState<Set<number>>(new Set());
  const [finalText, setFinalText] = useState("");
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState("");

  const analyze = async () => {
    if (markdown.trim().length < 10) {
      setError("请先粘贴需要统一风格的正文（至少 10 字）");
      return;
    }
    setLoading(true);
    setError("");
    setSegments([]);
    setFinalText("");
    try {
      const data = await rewriteStyle(markdown);
      setSegments(data.segments);
      setAccepted(new Set(data.segments.filter((item) => item.changed).map((item) => item.id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "分析失败");
    } finally {
      setLoading(false);
    }
  };

  const toggle = (id: number) => {
    setAccepted((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const apply = async () => {
    setApplying(true);
    setError("");
    try {
      const data = await assembleRewrite(markdown, segments, Array.from(accepted));
      setFinalText(data.markdown);
    } catch (err) {
      setError(err instanceof Error ? err.message : "应用失败");
    } finally {
      setApplying(false);
    }
  };

  const download = async () => {
    try {
      const blob = await renderDocx({
        markdown: finalText || markdown,
        title: "风格统一稿",
        template: "academic",
        toc: false,
        numbering: false,
        page_numbers: true,
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "风格统一稿.docx";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    }
  };

  const changedCount = segments.filter((item) => item.changed).length;

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">首页</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features" className="transition hover:text-brand-600">多部分整合</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">风格统一</span>
      </nav>

      <header className="mt-6 flex flex-wrap items-start gap-5">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-fuchsia-500 to-purple-500 text-white shadow-lg shadow-fuchsia-500/25">
          <Icon name="wand" className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">风格统一</h1>
          <p className="mt-2 text-sm text-slate-500">
            逐段改写成统一的学术书面语，每一段都能单独接受或回退——不是整篇一改到底。
          </p>
        </div>
      </header>

      <ModeTabs active="style" />

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-bold text-slate-800">原始正文</h2>
          <button
            type="button"
            onClick={() => setMarkdown(SAMPLE)}
            className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs text-slate-600 transition hover:border-slate-400"
          >
            填入示例
          </button>
        </div>
        <textarea
          value={markdown}
          onChange={(event) => setMarkdown(event.target.value)}
          rows={8}
          placeholder="粘贴需要统一风格的正文…"
          className="mt-3 w-full resize-y rounded-xl border border-slate-300 bg-slate-50/50 p-4 text-sm leading-7 text-slate-700 outline-none focus:border-fuchsia-400 focus:ring-2 focus:ring-fuchsia-100"
        />
        <div className="mt-3">
          <button
            type="button"
            onClick={analyze}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-fuchsia-500 to-purple-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-fuchsia-500/25 transition hover:-translate-y-0.5 disabled:opacity-50"
          >
            {loading ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                正在逐段改写…
              </>
            ) : (
              <>
                <Icon name="sparkles" className="h-4 w-4" />
                逐段改写
              </>
            )}
          </button>
        </div>
        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
        )}
      </section>

      {segments.length > 0 && (
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-bold text-slate-800">
              逐段对比
              <span className="ml-2 rounded-md bg-fuchsia-100 px-1.5 py-0.5 text-xs font-medium text-fuchsia-700">
                改动 {changedCount} / {segments.length} 段
              </span>
            </h2>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setAccepted(new Set(segments.filter((s) => s.changed).map((s) => s.id)))}
                className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs text-slate-600"
              >
                全选改动
              </button>
              <button
                type="button"
                onClick={() => setAccepted(new Set())}
                className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs text-slate-600"
              >
                全部还原
              </button>
            </div>
          </div>

          <ul className="mt-4 space-y-3">
            {segments.map((segment) => {
              const on = accepted.has(segment.id);
              return (
                <li
                  key={segment.id}
                  className={`rounded-xl border p-3 transition ${on ? "border-fuchsia-300 bg-fuchsia-50/40" : "border-slate-200"}`}
                >
                  <label className="flex items-start gap-2.5">
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() => toggle(segment.id)}
                      className="mt-1 h-4 w-4 rounded text-fuchsia-600"
                    />
                    <div className="min-w-0 flex-1">
                      {segment.changed ? (
                        <div className="grid gap-2 md:grid-cols-2">
                          <div className="rounded-lg bg-rose-50 px-3 py-2 text-xs leading-6 text-rose-900 line-through decoration-rose-300">
                            {segment.original}
                          </div>
                          <div className="rounded-lg bg-emerald-50 px-3 py-2 text-xs leading-6 text-emerald-900">
                            {segment.rewritten}
                          </div>
                        </div>
                      ) : (
                        <p className="rounded-lg bg-slate-50 px-3 py-2 text-xs leading-6 text-slate-500">
                          {segment.original}
                          <span className="ml-2 text-[11px] text-slate-400">（无需改动）</span>
                        </p>
                      )}
                      {segment.reason && (
                        <p className="mt-1.5 text-[11px] text-slate-500">改动说明：{segment.reason}</p>
                      )}
                    </div>
                  </label>
                </li>
              );
            })}
          </ul>

          <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-4">
            <button
              type="button"
              onClick={apply}
              disabled={applying}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
            >
              {applying ? "应用中…" : `应用选中的 ${accepted.size} 段`}
            </button>
            {finalText && (
              <button
                type="button"
                onClick={download}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-slate-400"
              >
                <Icon name="layout" className="h-4 w-4" />
                下载 Word
              </button>
            )}
          </div>
        </section>
      )}

      {finalText && (
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-5 py-3">
            <h2 className="text-sm font-bold text-slate-800">应用后的正文</h2>
          </div>
          <div className="max-h-[28rem] overflow-y-auto px-6 py-5">
            <MarkdownPreview markdown={finalText} />
          </div>
        </section>
      )}
    </main>
  );
}