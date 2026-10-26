"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { Icon } from "@/components/Icons";
import { MarkdownPreview } from "@/components/MarkdownPreview";
import {
  renderDocx,
  runOneClickStream,
  type AgentPlan,
  type CheckItem,
  type OneClickResponse,
  type PipelineStep,
} from "@/lib/api";

const ACCEPT = ".docx,.md,.markdown,.txt";

type Entry = { id: string; file: File; author: string; title: string };

function stem(name: string): string {
  return name.replace(/\.[^.]+$/, "");
}

const STATUS_STYLE: Record<PipelineStep["status"], string> = {
  ok: "bg-emerald-100 text-emerald-700",
  skipped: "bg-slate-100 text-slate-500",
  failed: "bg-rose-100 text-rose-700",
};

const STATUS_LABEL: Record<PipelineStep["status"], string> = {
  ok: "完成",
  skipped: "跳过",
  failed: "失败",
};

/**
 * 一键成稿主页面。
 *
 * 状态机是「待机 → 执行中 → 完成」：点击后先收到 plan 画出流水线骨架，
 * 再随 SSE 事件逐格点亮。排版导出是前端点击下载才发生的动作，
 * 因此结果到达时就把这一步标记为就绪，否则它会一直停在「等待」。
 */
export default function OneClickPage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [title, setTitle] = useState("小组作业合并稿");
  const [deai, setDeai] = useState(true);
  const [addTransitions, setAddTransitions] = useState(true);
  const [findReferences, setFindReferences] = useState(true);
  const [referenceLimit, setReferenceLimit] = useState(8);
  const [result, setResult] = useState<OneClickResponse | null>(null);
  const [plan, setPlan] = useState<string[]>([]);
  const [steps, setSteps] = useState<Record<string, PipelineStep>>({});
  const [agentPlan, setAgentPlan] = useState<AgentPlan | null>(null);
  const [checks, setChecks] = useState<CheckItem[]>([]);
  const [autoSaved, setAutoSaved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    const incoming = Array.from(list).slice(0, 20 - entries.length);
    setEntries((prev) => [
      ...prev,
      ...incoming.map((file) => ({
        id: `${file.name}-${file.size}-${Math.random().toString(36).slice(2, 8)}`,
        file,
        author: "",
        title: stem(file.name),
      })),
    ]);
    setResult(null);
    setPlan([]);
    setSteps({});
    setError("");
  };

  // 第一个还没回报的步骤视为"进行中"
  const runningIndex = plan.findIndex((name) => !steps[name]);

  const run = async () => {
    if (entries.length === 0) {
      setError("请先添加至少一份文稿");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    setPlan([]);
    setSteps({});
    setAgentPlan(null);
    setChecks([]);
    setAutoSaved(false);
    try {
      const data = await runOneClickStream(
        entries.map((entry) => entry.file),
        entries.map((entry) => ({ author: entry.author, title: entry.title })),
        title || "合并文稿",
        { deai, addTransitions, findReferences, referenceLimit },
        (event) => {
          if (event.type === "plan") {
            setPlan(event.steps);
          } else if (event.type === "step") {
            setSteps((prev) => ({ ...prev, [event.step.name]: event.step }));
          } else if (event.type === "agent") {
            setAgentPlan(event.plan);
          } else if (event.type === "verify") {
            setChecks(event.checks);
          } else if (event.type === "result") {
            setResult(event.data);
            // 成稿一到就自动导出 Word——用户点一次"一键生成"即可拿到成品，
            // 不需要再找下载按钮。浏览器若拦截下载，按钮仍然在。
            void autoDownload(event.data);
            // 排版导出是前端点击下载才发生的动作，结果到达即视为就绪
            setSteps((prev) => ({
              ...prev,
              "排版导出": {
                name: "排版导出",
                status: "ok",
                detail: "成稿已就绪，可下载 Word",
                elapsed_ms: 0,
              },
            }));
          }
        },
      );
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const autoDownload = async (data: OneClickResponse) => {
    try {
      const blob = await renderDocx({
        markdown: data.final_markdown,
        title: data.title,
        template: "academic",
        toc: true,
        numbering: true,
        page_numbers: true,
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = data.title + ".docx";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setAutoSaved(true);
    } catch {
      // 自动下载失败不影响流程，用户仍可手动点击下载
    }
  };

  const download = async () => {
    if (!result) return;
    setDownloading(true);
    setError("");
    try {
      const blob = await renderDocx({
        markdown: result.final_markdown,
        title: result.title,
        template: "academic",
        toc: true,
        numbering: true,
        page_numbers: true,
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${result.title}.docx`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">首页</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">一键成稿</span>
      </nav>

      <header className="mt-6 flex flex-wrap items-start gap-5">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 via-violet-600 to-cyan-500 text-white shadow-lg shadow-indigo-500/30">
          <Icon name="sparkles" className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">主链路</span>
            <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">可用</span>
          </div>
          <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">一键成稿</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            上传所有成员的文稿，自动完成：合并归一 → 补写过渡段 → 检索真实参考文献 → 排版导出 Word。全程约 15–40 秒。
          </p>
        </div>
      </header>

      {/* 上传 */}
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
          className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-9 text-center transition ${
            dragging ? "border-indigo-400 bg-indigo-50/60" : "border-slate-300 hover:border-indigo-300 hover:bg-slate-50"
          }`}
        >
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
            <Icon name="layers" className="h-5 w-5" />
          </span>
          <p className="mt-3 text-sm font-semibold text-slate-700">把成员文稿拖到这里，或点击选择</p>
          <p className="mt-1 text-xs text-slate-500">支持 .docx / .md / .txt，最多 20 份，单份 10MB</p>
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
          <ul className="mt-5 space-y-2">
            {entries.map((entry, index) => (
              <li key={entry.id} className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
                <div className="flex items-center gap-3">
                  <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white text-xs font-bold text-slate-500 shadow-sm">
                    {index + 1}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-800">{entry.file.name}</span>
                  <button
                    type="button"
                    onClick={() => setEntries((prev) => prev.filter((item) => item.id !== entry.id))}
                    className="rounded-md px-2 py-1 text-xs text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
                  >
                    移除
                  </button>
                </div>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  <input
                    value={entry.author}
                    onChange={(event) =>
                      setEntries((prev) =>
                        prev.map((item) => (item.id === entry.id ? { ...item, author: event.target.value } : item)),
                      )
                    }
                    placeholder="作者（如：张三）"
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-400"
                  />
                  <input
                    value={entry.title}
                    onChange={(event) =>
                      setEntries((prev) =>
                        prev.map((item) => (item.id === entry.id ? { ...item, title: event.target.value } : item)),
                      )
                    }
                    placeholder="章节名（留空用文稿内标题）"
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-400"
                  />
                </div>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-5 grid gap-3 border-t border-slate-100 pt-5 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-medium text-slate-500">成稿标题</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-400"
            />
          </label>
          <div className="flex flex-wrap items-end gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={addTransitions} onChange={(e) => setAddTransitions(e.target.checked)} className="h-4 w-4 rounded text-indigo-600" />
              补写过渡段
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={findReferences} onChange={(e) => setFindReferences(e.target.checked)} className="h-4 w-4 rounded text-indigo-600" />
              检索参考文献
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={deai} onChange={(e) => setDeai(e.target.checked)} className="h-4 w-4 rounded text-indigo-600" />
              去 AI 味
            </label>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={run}
            disabled={loading || entries.length === 0}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 via-violet-600 to-cyan-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                正在成稿（合并 → 过渡 → 文献）…
              </>
            ) : (
              <>
                <Icon name="sparkles" className="h-4 w-4" />
                一键生成
              </>
            )}
          </button>
          {entries.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setEntries([]);
                setResult(null);
              }}
              className="text-sm text-slate-500 transition hover:text-slate-800"
            >
              清空
            </button>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
        )}
      </section>

      {plan.length > 0 && (
        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-bold text-slate-800">
              执行流水线
              {result && (
                <span className="ml-2 rounded-md bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-700">
                  完成 · {(result.elapsed_ms / 1000).toFixed(1)} 秒
                </span>
              )}
            </h2>
            {loading && (
              <span className="flex items-center gap-1.5 text-xs text-indigo-600">
                <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
                实时执行中
              </span>
            )}
          </div>
          <ol className="mt-4 space-y-2">
            {plan.map((name, index) => {
              const step = steps[name];
              const running = !step && index === runningIndex && loading;
              const tone = running
                ? "border-indigo-300 bg-indigo-50/50"
                : step
                  ? "border-slate-200"
                  : "border-slate-100 opacity-60";
              return (
                <li
                  key={name}
                  className={"flex flex-wrap items-center gap-3 rounded-xl border px-3 py-2.5 transition " + tone}
                >
                  {step ? (
                    <span
                      className={"rounded-md px-1.5 py-0.5 text-[11px] font-medium " + STATUS_STYLE[step.status]}
                    >
                      {STATUS_LABEL[step.status]}
                    </span>
                  ) : running ? (
                    <span className="flex items-center gap-1.5 rounded-md bg-indigo-100 px-1.5 py-0.5 text-[11px] font-medium text-indigo-700">
                      <span className="h-2 w-2 animate-spin rounded-full border border-indigo-500/40 border-t-indigo-600" />
                      进行中
                    </span>
                  ) : (
                    <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-400">
                      等待
                    </span>
                  )}
                  <span className="text-sm font-medium text-slate-800">{name}</span>
                  <span className="min-w-0 flex-1 truncate text-xs text-slate-500">
                    {step ? step.detail : ""}
                  </span>
                  {step && <span className="text-xs tabular-nums text-slate-400">{step.elapsed_ms}ms</span>}
                </li>
              );
            })}
          </ol>
          {result && (
            <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-4">
              <button
                type="button"
                onClick={download}
                disabled={downloading}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
              >
                <Icon name="layout" className="h-4 w-4" />
                {downloading ? "正在排版…" : "重新下载 Word 成稿"}
              </button>
              {autoSaved && (
                <span className="inline-flex items-center gap-1.5 self-center text-xs text-emerald-600">
                  <Icon name="check" className="h-3.5 w-3.5" />
                  已自动下载，可直接提交
                </span>
              )}
              <button
                type="button"
                onClick={() => setShowPreview((prev) => !prev)}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-slate-400"
              >
                {showPreview ? "收起预览" : "查看成稿预览"}
              </button>
            </div>
          )}
          {result && result.warnings.length > 0 && (
            <ul className="mt-3 space-y-1">
              {result.warnings.map((warning) => (
                <li key={warning} className="text-xs text-amber-700">· {warning}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {agentPlan && (
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-bold text-slate-800">
            Agent 决策
            <span className="ml-2 rounded-md bg-violet-100 px-1.5 py-0.5 text-xs font-medium text-violet-700">
              {agentPlan.source === "model"
                ? "模型规划"
                : agentPlan.source === "fallback"
                  ? "规划失败 · 沿用用户设置"
                  : "用户指定"}
            </span>
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{agentPlan.reasoning}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span
              className={
                "rounded-full border px-2.5 py-1 " +
                (agentPlan.need_transitions
                  ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                  : "border-slate-200 text-slate-400")
              }
            >
              {agentPlan.need_transitions ? "补写过渡段" : "跳过过渡段"}
            </span>
            <span
              className={
                "rounded-full border px-2.5 py-1 " +
                (agentPlan.need_references
                  ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                  : "border-slate-200 text-slate-400")
              }
            >
              {agentPlan.need_references
                ? "检索参考文献（" + agentPlan.reference_limit + " 条）"
                : "跳过参考文献"}
            </span>
          </div>
          {agentPlan.transition_hint && (
            <p className="mt-2 text-xs text-slate-500">过渡判断：{agentPlan.transition_hint}</p>
          )}
        </section>
      )}

      {checks.length > 0 && (
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-bold text-slate-800">
            自检结果
            <span
              className={
                "ml-2 rounded-md px-1.5 py-0.5 text-xs font-medium " +
                (checks.every((item) => item.ok)
                  ? "bg-emerald-100 text-emerald-700"
                  : "bg-amber-100 text-amber-700")
              }
            >
              {checks.filter((item) => item.ok).length}/{checks.length} 通过
            </span>
          </h2>
          <ul className="mt-3 space-y-1.5">
            {checks.map((item) => (
              <li key={item.name} className="flex flex-wrap items-center gap-2 text-xs">
                <span className={item.ok ? "text-emerald-600" : "text-amber-600"}>
                  {item.ok ? "✓" : "!"}
                </span>
                <span className="font-medium text-slate-700">{item.name}</span>
                <span className="text-slate-500">{item.detail}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {result && (
        <div className="mt-6 space-y-6">

          {result.references.inserted > 0 && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-bold text-slate-800">
                自动检索的参考文献
                <span className="ml-2 rounded-md bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-700">
                  {result.references.inserted} 条
                </span>
              </h2>
              {result.references.queries && (
                <p className="mt-2 text-xs text-slate-500">
                  检索关键词：{result.references.queries.join("、")}
                </p>
              )}
              <ul className="mt-3 space-y-2">
                {result.references.entries.map((entry) => (
                  <li key={entry.index} className="rounded-lg bg-slate-50 px-3 py-2 text-xs leading-6 text-slate-700">
                    {entry.text}
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-slate-400">
                全部来自 OpenAlex / Crossref 的真实记录，可点 DOI 核实。
              </p>
            </section>
          )}

          {showPreview && (
            <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 px-5 py-3">
                <h2 className="text-sm font-bold text-slate-800">成稿预览</h2>
              </div>
              <div className="max-h-[32rem] overflow-y-auto px-6 py-5">
                <MarkdownPreview markdown={result.final_markdown} />
              </div>
            </section>
          )}
        </div>
      )}
    </main>
  );
}