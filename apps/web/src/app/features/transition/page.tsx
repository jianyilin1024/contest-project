"use client";

import Link from "next/link";
import { Fragment, useCallback, useEffect, useMemo, useState } from "react";

import { Icon } from "@/components/Icons";
import { MarkdownPreview } from "@/components/MarkdownPreview";
import {
  analyzeTransitions,
  applyTransitions,
  renderDocx,
  type TransitionBoundary,
  type TransitionBlock,
  type TransitionResponse,
} from "@/lib/api";

const SAMPLE = `# 基于小样本学习的图像分类方法研究

## 1 研究背景

深度学习的快速发展推动了图像分类技术的进步，卷积神经网络在大规模数据集上已经取得很高的准确率。

然而在医疗影像、工业质检等实际场景中，标注样本往往十分有限，模型容易过拟合。

## 2 研究方法

本文采用元学习框架，构建了基于任务采样的训练流程。

模型主干选用 ResNet-18，并在每个任务内进行五次梯度更新。

## 3 实验结果

在 MiniImageNet 的 5-way 1-shot 设置下，本文方法取得 62.3% 的准确率。

相比基线方法提升了 4.1 个百分点。

## 4 结论

本文提出的方法在小样本条件下具备良好的泛化能力。
`;

type Selection = { id: string; custom: string };

function blockClass(block: TransitionBlock): string {
  if (block.kind === "heading") return block.level <= 1 ? "text-xl font-bold text-slate-900" : "text-base font-bold text-slate-800";
  if (block.kind === "quote") return "border-l-4 border-indigo-200 bg-indigo-50/40 px-4 py-2 text-sm text-slate-600";
  if (block.kind === "table") return "font-mono text-xs text-slate-500";
  return "text-sm leading-7 text-slate-700";
}

export default function TransitionPage() {
  const [markdown, setMarkdown] = useState("");
  const [title, setTitle] = useState("小样本学习研究");
  const [result, setResult] = useState<TransitionResponse | null>(null);
  const [selections, setSelections] = useState<Record<string, Selection>>({});
  const [view, setView] = useState<"edit" | "preview">("edit");
  const [preview, setPreview] = useState("");
  const [insertedCount, setInsertedCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const stashed = window.sessionStorage.getItem("transition:markdown");
    if (stashed) {
      // sessionStorage 仅在浏览器端可用，必须在挂载后读取
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMarkdown(stashed);
      window.sessionStorage.removeItem("transition:markdown");
    }
  }, []);

  const neededBoundaries = useMemo(
    () => (result ? result.boundaries.filter((item) => item.needs && item.options.length > 0) : []),
    [result],
  );

  const insertions = useMemo(() => {
    const items: { after_block_id: number; text: string }[] = [];
    for (const boundary of neededBoundaries) {
      const selection = selections[boundary.id];
      if (!selection || selection.id === "none") continue;
      let text = "";
      if (selection.id === "custom") {
        text = selection.custom.trim();
      } else {
        text = boundary.options.find((option) => option.id === selection.id)?.text ?? "";
      }
      if (text) items.push({ after_block_id: boundary.after_block_id, text });
    }
    return items;
  }, [neededBoundaries, selections]);

  const refreshPreview = useCallback(async () => {
    if (!result) return;
    setApplying(true);
    try {
      const data = await applyTransitions(result.blocks, insertions);
      setPreview(data.markdown);
      setInsertedCount(data.inserted);
    } catch (err) {
      setError(err instanceof Error ? err.message : "预览生成失败");
    } finally {
      setApplying(false);
    }
  }, [result, insertions]);

  const openPreview = () => {
    setView("preview");
    void refreshPreview();
  };

  const run = async () => {
    if (!markdown.trim()) {
      setError("请先粘贴文档内容");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    setPreview("");
    try {
      const data = await analyzeTransitions(markdown, title);
      const initial: Record<string, Selection> = {};
      for (const boundary of data.boundaries) {
        if (!boundary.needs || boundary.options.length === 0) continue;
        const preferred = boundary.options.find((option) => !option.duplicate) ?? boundary.options[0];
        initial[boundary.id] = { id: preferred.id, custom: "" };
      }
      setResult(data);
      setSelections(initial);
      setView("edit");
    } catch (err) {
      setError(err instanceof Error ? err.message : "分析失败");
    } finally {
      setLoading(false);
    }
  };

  const download = async (format: "md" | "docx") => {
    let content = preview;
    if (!content) {
      if (!result) return;
      try {
        const data = await applyTransitions(result.blocks, insertions);
        content = data.markdown;
        setPreview(content);
      } catch (err) {
        setError(err instanceof Error ? err.message : "生成失败");
        return;
      }
    }
    try {
      const blob =
        format === "md"
          ? new Blob([content], { type: "text/markdown;charset=utf-8" })
          : await renderDocx({
              markdown: content,
              title,
              template: "academic",
              toc: true,
              numbering: true,
              page_numbers: true,
            });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${title || "文档"}.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    }
  };

  const setSelection = (boundaryId: string, patch: Partial<Selection>) => {
    setSelections((prev) => ({
      ...prev,
      [boundaryId]: { ...(prev[boundaryId] ?? { id: "none", custom: "" }), ...patch },
    }));
  };

  const boundaryById = (blockId: number): TransitionBoundary | undefined =>
    neededBoundaries.find((item) => item.after_block_id === blockId);

  return (
    <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">首页</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features" className="transition hover:text-brand-600">功能分区</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">过渡段落生成</span>
      </nav>

      <header className="mt-6 flex flex-wrap items-start gap-5">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500 to-orange-500 text-white shadow-lg shadow-amber-500/25">
          <Icon name="link" className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-900/5 px-2 py-0.5 text-xs font-bold text-slate-500">F3</span>
            <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">可用</span>
          </div>
          <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">过渡段落生成</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            AI 先判断哪些章节之间缺少衔接，再给出多个风格的备选段落。你可以逐处勾选采用或不采用，确认后再导出。
          </p>
        </div>
      </header>

      {/* 输入 */}
      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-bold text-slate-800">文档内容（Markdown）</h2>
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
          placeholder="把合并稿粘贴到这里，点击「分析衔接点」"
          className="mt-3 h-44 w-full resize-y rounded-xl border border-slate-300 bg-slate-50/50 p-4 font-mono text-xs leading-6 text-slate-700 outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
        />
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="text-xs font-medium text-slate-500">文档标题</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="mt-1 w-56 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
            />
          </label>
          <button
            type="button"
            onClick={run}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-amber-500/25 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                正在分析衔接点…
              </>
            ) : (
              <>
                <Icon name="sparkles" className="h-4 w-4" />
                分析衔接点
              </>
            )}
          </button>
        </div>
        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
        )}
      </section>

      {result && (
        <>
          {/* 统计与视图切换 */}
          <section className="mt-6 flex flex-wrap items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
              <span className="text-slate-500">
                候选衔接点 <strong className="text-slate-900">{result.stats.candidates}</strong>
              </span>
              <span className="text-slate-500">
                建议插入 <strong className="text-amber-600">{result.stats.needed}</strong>
              </span>
              <span className="text-slate-500">
                已选 <strong className="text-emerald-600">{insertions.length}</strong> 处
              </span>
              <span className="text-slate-400">{(result.elapsed_ms / 1000).toFixed(1)}s</span>
            </div>
            <div className="ml-auto flex gap-1 rounded-lg bg-slate-100 p-1">
              {[
                { key: "edit" as const, label: "逐处确认" },
                { key: "preview" as const, label: "应用后预览" },
              ].map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => {
                    if (item.key === "preview") {
                      openPreview();
                    } else {
                      setView("edit");
                    }
                  }}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                    view === item.key ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => download("md")}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-400"
              >
                导出 .md
              </button>
              <button
                type="button"
                onClick={() => download("docx")}
                className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-slate-800"
              >
                导出 .docx
              </button>
            </div>
          </section>

          {view === "edit" ? (
            <section className="mt-6 space-y-4">
              {result.blocks.map((block) => {
                const boundary = boundaryById(block.id);
                return (
                  <Fragment key={block.id}>
                    <div className={blockClass(block)}>
                      {block.kind === "list" ? `· ${block.text}` : block.text}
                    </div>
                    {boundary && (
                      <TransitionCard
                        boundary={boundary}
                        selection={selections[boundary.id] ?? { id: "none", custom: "" }}
                        onChange={(patch) => setSelection(boundary.id, patch)}
                      />
                    )}
                  </Fragment>
                );
              })}
            </section>
          ) : (
            <section className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
                <h2 className="text-sm font-bold text-slate-800">应用后预览</h2>
                <span className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">
                    {applying ? "生成中…" : `已插入 ${insertedCount} 处过渡段`}
                  </span>
                  <button
                    type="button"
                    onClick={() => void refreshPreview()}
                    className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs text-slate-600 transition hover:border-slate-400"
                  >
                    刷新
                  </button>
                </span>
              </div>
              <div className="max-h-[36rem] overflow-y-auto px-6 py-5">
                {preview ? <MarkdownPreview markdown={preview} /> : <p className="text-sm text-slate-400">生成中…</p>}
              </div>
            </section>
          )}
        </>
      )}
    </main>
  );
}

function TransitionCard({
  boundary,
  selection,
  onChange,
}: {
  boundary: TransitionBoundary;
  selection: Selection;
  onChange: (patch: Partial<Selection>) => void;
}) {
  return (
    <div className="my-4 rounded-2xl border-2 border-dashed border-amber-300 bg-amber-50/40 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Icon name="link" className="h-4 w-4 text-amber-600" />
        <span className="text-xs font-medium text-slate-600">
          {boundary.section_from} → {boundary.section_to}
        </span>
        <span className="rounded-md bg-amber-200/60 px-1.5 py-0.5 text-[11px] font-medium text-amber-800">
          置信度 {Math.round(boundary.confidence * 100)}%
        </span>
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-600">{boundary.reason}</p>

      <div className="mt-3 space-y-2">
        {boundary.options.map((option) => {
          const active = selection.id === option.id;
          return (
            <label
              key={option.id}
              className={`flex cursor-pointer gap-2.5 rounded-xl border bg-white p-3 transition ${
                active ? "border-amber-400 ring-2 ring-amber-100" : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <input
                type="radio"
                name={boundary.id}
                checked={active}
                onChange={() => onChange({ id: option.id })}
                className="mt-1 h-4 w-4 shrink-0 text-amber-600 focus:ring-amber-400"
              />
              <span className="min-w-0">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600">
                    {option.label}
                  </span>
                  {option.duplicate && (
                    <span className="rounded-md bg-rose-100 px-1.5 py-0.5 text-[11px] font-medium text-rose-700">
                      与下文重复度较高
                    </span>
                  )}
                </span>
                <span className="mt-1 block text-sm leading-6 text-slate-800">{option.text}</span>
              </span>
            </label>
          );
        })}

        <label
          className={`flex cursor-pointer items-center gap-2.5 rounded-xl border bg-white p-3 transition ${
            selection.id === "custom" ? "border-amber-400 ring-2 ring-amber-100" : "border-slate-200 hover:border-slate-300"
          }`}
        >
          <input
            type="radio"
            name={boundary.id}
            checked={selection.id === "custom"}
            onChange={() => onChange({ id: "custom" })}
            className="h-4 w-4 shrink-0 text-amber-600 focus:ring-amber-400"
          />
          <span className="text-sm text-slate-700">自己写一句</span>
        </label>
        {selection.id === "custom" && (
          <textarea
            value={selection.custom}
            onChange={(event) => onChange({ custom: event.target.value })}
            placeholder="输入你自己的过渡文字…"
            className="w-full rounded-xl border border-slate-300 p-3 text-sm outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
            rows={2}
          />
        )}

        <label
          className={`flex cursor-pointer items-center gap-2.5 rounded-xl border p-3 transition ${
            selection.id === "none"
              ? "border-slate-400 bg-slate-50"
              : "border-slate-200 bg-white hover:border-slate-300"
          }`}
        >
          <input
            type="radio"
            name={boundary.id}
            checked={selection.id === "none"}
            onChange={() => onChange({ id: "none" })}
            className="h-4 w-4 shrink-0 text-slate-600 focus:ring-slate-400"
          />
          <span className="text-sm text-slate-600">不插入（保持原样）</span>
        </label>
      </div>
    </div>
  );
}
