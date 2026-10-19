"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { Icon } from "@/components/Icons";
import { MarkdownPreview } from "@/components/MarkdownPreview";
import { ModeTabs } from "@/components/merge/ModeTabs";
import {
  analyzeSingle,
  exportMerge,
  unifyDocument,
  type SingleAnalysisResponse,
  type UnifyResponse,
} from "@/lib/api";

const ACCEPT = ".docx,.md,.markdown,.txt";

const GROUP_STYLE = [
  { chip: "bg-indigo-100 text-indigo-700", bar: "bg-indigo-500" },
  { chip: "bg-emerald-100 text-emerald-700", bar: "bg-emerald-500" },
  { chip: "bg-amber-100 text-amber-700", bar: "bg-amber-500" },
  { chip: "bg-rose-100 text-rose-700", bar: "bg-rose-500" },
  { chip: "bg-cyan-100 text-cyan-700", bar: "bg-cyan-500" },
];

const HETERO: Record<string, { label: string; cls: string }> = {
  low: { label: "文风一致", cls: "bg-emerald-100 text-emerald-700" },
  medium: { label: "轻度差异", cls: "bg-amber-100 text-amber-700" },
  high: { label: "差异明显", cls: "bg-rose-100 text-rose-700" },
};

const ISSUE_LABEL: Record<string, string> = {
  terminology: "术语",
  sentence_length: "句长",
  person: "人称",
  tone: "语气",
  punctuation: "标点",
  connective: "连接词",
  structure: "结构",
};

export default function SingleAnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [docTitle, setDocTitle] = useState("");
  const [result, setResult] = useState<SingleAnalysisResponse | null>(null);
  const [unified, setUnified] = useState<UnifyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [unifying, setUnifying] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [activeGroup, setActiveGroup] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const pick = (incoming: FileList | null) => {
    const chosen = incoming?.[0];
    if (!chosen) return;
    setFile(chosen);
    setDocTitle((prev) => prev || chosen.name.replace(/\.[^.]+$/, ""));
    setResult(null);
    setUnified(null);
    setError("");
  };

  const run = async () => {
    if (!file) {
      setError("请先选择一份文档");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    setUnified(null);
    try {
      const data = await analyzeSingle(file, docTitle || file.name);
      setResult(data);
      const dominant = [...data.authorship.groups].sort((a, b) => b.units - a.units)[0];
      setActiveGroup(dominant?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "分析失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const runUnify = async () => {
    if (!result) return;
    setUnifying(true);
    setError("");
    try {
      const groupOf: Record<number, string> = {};
      for (const item of result.authorship.assignments) {
        groupOf[item.unit_id] = item.group_id;
      }
      const segments = result.segments.map((segment) => ({
        id: segment.id,
        section: segment.section,
        text: segment.text,
        group_id: groupOf[segment.id] ?? "",
      }));
      const data = await unifyDocument(
        segments,
        result.style.canonical_style,
        `${result.title}（文风归并稿）`,
        activeGroup,
      );
      setUnified(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成归并稿失败");
    } finally {
      setUnifying(false);
    }
  };

  const download = async (format: "md" | "docx") => {
    if (!unified) return;
    try {
      const blob = await exportMerge(unified.markdown, `${result?.title ?? "文档"}（文风归并稿）`, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${result?.title ?? "文档"}（文风归并稿）.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    }
  };

  const groupIndex = (id: string) => {
    const index = result?.authorship.groups.findIndex((group) => group.id === id) ?? -1;
    return index >= 0 ? index % GROUP_STYLE.length : 0;
  };

  return (
    <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">首页</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features" className="transition hover:text-brand-600">功能分区</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features/merge" className="transition hover:text-brand-600">多部分整合</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">单文档 AI 分析</span>
      </nav>

      <ModeTabs active="single" />

      <header className="mt-8 flex flex-wrap items-start gap-5">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-fuchsia-500 to-purple-500 text-white shadow-lg shadow-fuchsia-500/25">
          <Icon name="wand" className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-900/5 px-2 py-0.5 text-xs font-bold text-slate-500">F1</span>
            <span className="rounded-md bg-fuchsia-100 px-2 py-0.5 text-xs font-medium text-fuchsia-700">AI 分析</span>
          </div>
          <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">单文档 AI 分析</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            只上传一篇文档，AI 逐段比对写作特征，推测哪些部分可能出自不同人，并给出文风归并建议、版式识别结果和可下载的归并稿。
          </p>
        </div>
      </header>

      {/* ================= 上传 ================= */}
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
            pick(event.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragging ? "border-fuchsia-400 bg-fuchsia-50/60" : "border-slate-300 hover:border-fuchsia-300 hover:bg-slate-50"
          }`}
        >
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-fuchsia-50 text-fuchsia-600">
            <Icon name="wand" className="h-5 w-5" />
          </span>
          <p className="mt-4 text-sm font-semibold text-slate-700">
            {file ? file.name : "把文档拖到这里，或点击选择"}
          </p>
          <p className="mt-1.5 text-xs text-slate-500">
            支持 .docx / .md / .txt，单份 10MB。分析约需 15–40 秒
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

        <div className="mt-5 flex flex-wrap items-end gap-4 border-t border-slate-100 pt-5">
          <label className="block">
            <span className="text-xs font-medium text-slate-500">文档标题</span>
            <input
              value={docTitle}
              onChange={(event) => setDocTitle(event.target.value)}
              placeholder="留空则用文件名"
              className="mt-1 w-64 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-fuchsia-400 focus:ring-2 focus:ring-fuchsia-100"
            />
          </label>
          <button
            type="button"
            onClick={run}
            disabled={loading || !file}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-fuchsia-600 to-purple-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-fuchsia-500/25 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {loading ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                AI 正在逐段分析…
              </>
            ) : (
              <>
                <Icon name="sparkles" className="h-4 w-4" />
                开始分析
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}
      </section>

      {result && (
        <div className="mt-8 space-y-6">
          {/* 统计 */}
          <section className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            {[
              { label: "章节", value: result.stats.sections },
              { label: "段落", value: result.stats.paragraphs },
              { label: "字数", value: result.stats.characters },
              { label: "分析单元", value: result.stats.units_analyzed },
              { label: "耗时", value: `${(result.elapsed_ms / 1000).toFixed(1)}s` },
            ].map((card) => (
              <div key={card.label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-2xl font-extrabold text-slate-900">{card.value}</p>
                <p className="mt-0.5 text-xs text-slate-500">{card.label}</p>
              </div>
            ))}
          </section>

          {/* 异质性结论 */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-sm font-bold text-slate-800">文风异质性判断</h2>
              <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${(HETERO[result.authorship.heterogeneity] ?? HETERO.low).cls}`}>
                {(HETERO[result.authorship.heterogeneity] ?? HETERO.low).label}
              </span>
              <span className="text-xs text-slate-400">模型 {result.model}</span>
            </div>
            <p className="mt-3 text-sm leading-7 text-slate-700">{result.authorship.conclusion}</p>
            <p className="mt-2 text-xs text-slate-400">
              这是基于统计特征与文本内容的推测，不是事实认定；请结合实际情况判断。
            </p>
          </section>

          {/* 文风分组 */}
          <section>
            <h2 className="text-sm font-bold text-slate-800">文风分组</h2>
            <p className="mt-1 text-xs text-slate-500">点击卡片可高亮该组，并把它设为目标文风（归并时其他组向它靠拢）。</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {result.authorship.groups.map((group) => {
                const style = GROUP_STYLE[groupIndex(group.id)];
                const isActive = activeGroup === group.id;
                return (
                  <button
                    type="button"
                    key={group.id}
                    onClick={() => setActiveGroup(group.id)}
                    className={`card-lift rounded-2xl border bg-white p-5 text-left shadow-sm transition ${
                      isActive ? "border-indigo-400 ring-2 ring-indigo-100" : "border-slate-200"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`rounded-md px-2 py-0.5 text-xs font-bold ${style.chip}`}>{group.id}</span>
                      {isActive && <span className="text-xs font-medium text-indigo-600">目标文风</span>}
                    </div>
                    <h3 className="mt-2.5 text-sm font-bold text-slate-900">{group.label}</h3>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span>{group.units} 段</span>
                      <span>{group.characters} 字</span>
                      <span>平均句长 {group.avg_sentence}</span>
                    </div>
                    <ul className="mt-3 space-y-1.5">
                      {group.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-1.5 text-xs leading-5 text-slate-600">
                          <span className={`mt-1.5 h-1 w-1 shrink-0 rounded-full ${style.bar}`} />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </button>
                );
              })}
            </div>
          </section>

          {/* 段落归属 */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-800">逐段归属与依据</h2>
            <ul className="mt-4 space-y-2">
              {result.authorship.assignments.map((item) => {
                const style = GROUP_STYLE[groupIndex(item.group_id)];
                return (
                  <li key={item.unit_id} className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs text-slate-400">#{item.unit_id}</span>
                      <span className={`rounded-md px-1.5 py-0.5 text-[11px] font-bold ${style.chip}`}>{item.group_id}</span>
                      <span className="text-xs text-slate-500">{item.section}</span>
                      <span className="ml-auto flex items-center gap-2">
                        <span className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200">
                          <span
                            className={`block h-full rounded-full ${style.bar}`}
                            style={{ width: `${Math.round(item.confidence * 100)}%` }}
                          />
                        </span>
                        <span className="text-xs tabular-nums text-slate-500">
                          {Math.round(item.confidence * 100)}%
                        </span>
                      </span>
                    </div>
                    <p className="mt-1.5 text-xs leading-5 text-slate-500">{item.reason}</p>
                    <p className="mt-1 text-sm leading-6 text-slate-700">{item.preview}…</p>
                  </li>
                );
              })}
            </ul>
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* 文风归并建议 */}
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-bold text-slate-800">文风归并建议</h2>
              <div className="mt-3 rounded-xl border border-indigo-100 bg-indigo-50/50 p-4">
                <p className="text-xs font-semibold text-indigo-700">建议统一到</p>
                <p className="mt-1 text-sm leading-6 text-slate-700">{result.style.canonical_style}</p>
              </div>
              <ul className="mt-4 space-y-3">
                {result.style.issues.map((issue, index) => (
                  <li key={index} className="rounded-xl border border-slate-200 p-3">
                    <div className="flex items-center gap-2">
                      <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600">
                        {ISSUE_LABEL[issue.type] ?? issue.type}
                      </span>
                      <span className="text-sm font-semibold text-slate-800">{issue.title}</span>
                    </div>
                    <p className="mt-1.5 text-xs leading-5 text-slate-600">{issue.detail}</p>
                    {issue.examples.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {issue.examples.map((example, exampleIndex) => (
                          <li key={exampleIndex} className="rounded-md bg-slate-50 px-2 py-1 text-xs text-slate-500">
                            {example}
                          </li>
                        ))}
                      </ul>
                    )}
                    <p className="mt-2 text-xs leading-5 text-indigo-700">→ {issue.suggestion}</p>
                  </li>
                ))}
              </ul>
              {result.style.plan.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold text-slate-500">执行顺序</p>
                  <ol className="mt-2 space-y-1">
                    {result.style.plan.map((step, index) => (
                      <li key={index} className="flex gap-2 text-xs leading-5 text-slate-600">
                        <span className="font-mono text-slate-400">{index + 1}.</span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </section>

            {/* 版式识别 */}
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-bold text-slate-800">版式识别</h2>
              <p className="mt-3 text-sm leading-7 text-slate-700">{result.layout.summary}</p>
              <ul className="mt-4 space-y-3">
                {result.layout.conventions.map((item, index) => (
                  <li key={index} className="rounded-xl border border-slate-200 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-slate-800">{item.aspect}</span>
                      <span
                        className={`rounded-md px-1.5 py-0.5 text-[11px] font-medium ${
                          item.consistent ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {item.consistent ? "一致" : "需调整"}
                      </span>
                    </div>
                    <p className="mt-1.5 text-xs leading-5 text-slate-600">{item.observation}</p>
                    {item.suggestion && (
                      <p className="mt-1.5 text-xs leading-5 text-indigo-700">→ {item.suggestion}</p>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          </div>

          {/* 归并稿 */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-slate-800">文风归并稿</h2>
                <p className="mt-1 text-xs text-slate-500">
                  把非目标文风的段落改写为
                  {activeGroup ? `「${result.authorship.groups.find((g) => g.id === activeGroup)?.label ?? activeGroup}」` : "建议文风"}
                  ，原意与数据不变。
                </p>
              </div>
              <button
                type="button"
                onClick={runUnify}
                disabled={unifying}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {unifying ? (
                  <>
                    <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                    正在改写…
                  </>
                ) : (
                  <>
                    <Icon name="wand" className="h-4 w-4" />
                    生成归并稿
                  </>
                )}
              </button>
            </div>

            {unified && (
              <>
                <div className="mt-4 flex flex-wrap items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
                  <span className="text-sm text-emerald-800">
                    已改写 {unified.rewritten} 段
                    {unified.failed > 0 && `，失败 ${unified.failed} 段`}
                  </span>
                  <span className="ml-auto flex gap-2">
                    <button
                      type="button"
                      onClick={() => download("md")}
                      className="rounded-lg border border-emerald-300 bg-white px-3 py-1.5 text-xs font-medium text-emerald-800 transition hover:border-emerald-400"
                    >
                      下载 .md
                    </button>
                    <button
                      type="button"
                      onClick={() => download("docx")}
                      className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-emerald-600"
                    >
                      下载 .docx
                    </button>
                  </span>
                </div>
                <div className="mt-4 max-h-[32rem] overflow-y-auto rounded-xl border border-slate-100 px-5 py-4">
                  <MarkdownPreview markdown={unified.markdown} />
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
