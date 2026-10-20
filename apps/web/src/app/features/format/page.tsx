"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icons";
import { MarkdownPreview } from "@/components/MarkdownPreview";
import {
  fetchTemplates,
  formatReferences,
  renderDocx,
  type ReferenceResponse,
  type TemplateInfo,
} from "@/lib/api";

const SAMPLE = `# 小组作业合并稿

## 1 绪论

### 1.1 研究背景

随着深度学习的发展，卷积神经网络已经成为图像分类任务中的主流方法。本文关注小样本条件下的模型泛化能力问题。

## 2 研究方法

### 2.1 模型选择

本文采用卷积神经网络作为基础模型，并在小样本数据集上开展实验。

### 2.2 数据集

实验数据来自公开数据集 MiniImageNet，共 60000 张图片。

## 3 结论

实验结果表明，该方法在小样本条件下具备良好的泛化能力。

## 参考文献

[1] 张三, 李四. 深度学习综述[J]. 计算机学报, 2023, 46(5): 1-20.
[2] 王五. 小样本学习[M]. 北京: 科学出版社, 2022.
`;

export default function FormatPage() {
  const [markdown, setMarkdown] = useState("");
  const [title, setTitle] = useState("小组作业合并稿");
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [templateKey, setTemplateKey] = useState("academic");
  // 选项以"用户覆盖值"为准，未覆盖时取模板默认值——避免在 effect 里同步 state
  const [overrides, setOverrides] = useState<{
    toc?: boolean;
    numbering?: boolean;
    pageNumbers?: boolean;
  }>({});
  const [exporting, setExporting] = useState(false);
  const [refLoading, setRefLoading] = useState(false);
  const [refResult, setRefResult] = useState<ReferenceResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchTemplates()
      .then((data) => setTemplates(data))
      .catch(() => setTemplates([]));

    const stashed = window.sessionStorage.getItem("format:markdown");
    if (stashed) {
      // sessionStorage 只在浏览器端存在，必须在挂载后才能读取，
      // 因此这里同步 setState 是必要的（否则会与服务端渲染结果不一致）
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMarkdown(stashed);
      window.sessionStorage.removeItem("format:markdown");
    }
  }, []);

  const selected = templates.find((item) => item.key === templateKey);
  const toc = overrides.toc ?? selected?.toc ?? true;
  const numbering = overrides.numbering ?? selected?.numbering ?? true;
  const pageNumbers = overrides.pageNumbers ?? selected?.page_numbers ?? true;

  const runExport = async () => {
    if (!markdown.trim()) {
      setError("请先粘贴或导入待排版的文稿");
      return;
    }
    setExporting(true);
    setError("");
    try {
      const blob = await renderDocx({ markdown, title, template: templateKey, toc, numbering, page_numbers: pageNumbers });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${title || "排版稿"}.docx`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    } finally {
      setExporting(false);
    }
  };

  const runReferences = async () => {
    if (!markdown.trim()) {
      setError("请先粘贴文稿");
      return;
    }
    setRefLoading(true);
    setError("");
    try {
      const data = await formatReferences(markdown);
      setRefResult(data);
      if (data.found && data.markdown) {
        setMarkdown(data.markdown);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "规范化失败");
    } finally {
      setRefLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">首页</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features" className="transition hover:text-brand-600">功能分区</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">AI 辅助排版</span>
      </nav>

      <header className="mt-6 flex flex-wrap items-start gap-5">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-lg shadow-sky-500/25">
          <Icon name="layout" className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-900/5 px-2 py-0.5 text-xs font-bold text-slate-500">F5</span>
            <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">可用</span>
          </div>
          <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">AI 辅助排版</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            把合并稿按模板渲染成规范 Word 文档：自动编号、生成目录、加页码，并可让 AI 把参考文献整理成 GB/T 7714-2015 格式。
          </p>
        </div>
      </header>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        {/* 编辑器 */}
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-bold text-slate-800">文稿内容（Markdown）</h2>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setMarkdown(SAMPLE)}
                className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs text-slate-600 transition hover:border-slate-400"
              >
                填入示例
              </button>
              <button
                type="button"
                onClick={() => {
                  setMarkdown("");
                  setRefResult(null);
                }}
                className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs text-slate-600 transition hover:border-slate-400"
              >
                清空
              </button>
            </div>
          </div>
          <textarea
            value={markdown}
            onChange={(event) => setMarkdown(event.target.value)}
            placeholder={"把合并稿粘贴到这里，或从「多部分整合」的结果页点击「去排版」带过来。\n\n支持 # 标题、- 列表、> 引用、| 表格。".replace(/\\n/g, "\n")}
            className="mt-3 h-80 w-full resize-y rounded-xl border border-slate-300 bg-slate-50/50 p-4 font-mono text-xs leading-6 text-slate-700 outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
          />
        </section>

        {/* 设置 */}
        <section className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-800">排版模板</h2>
            <div className="mt-3 space-y-2">
              {templates.map((item) => {
                const active = item.key === templateKey;
                return (
                  <button
                    type="button"
                    key={item.key}
                    onClick={() => {
                      setTemplateKey(item.key);
                      setOverrides({});
                    }}
                    className={`w-full rounded-xl border p-3 text-left transition ${
                      active ? "border-sky-400 bg-sky-50/60 ring-2 ring-sky-100" : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <span className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-slate-800">{item.name}</span>
                      {active && <Icon name="check" className="h-4 w-4 text-sky-600" />}
                    </span>
                    <span className="mt-1 block text-xs leading-5 text-slate-500">{item.description}</span>
                  </button>
                );
              })}
              {templates.length === 0 && <p className="text-xs text-slate-400">模板加载中…</p>}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-800">选项</h2>
            <div className="mt-3 space-y-2.5">
              {[
                {
                  label: "生成目录",
                  checked: toc,
                  onChange: (value: boolean) => setOverrides((prev) => ({ ...prev, toc: value })),
                },
                {
                  label: "标题自动编号",
                  checked: numbering,
                  onChange: (value: boolean) => setOverrides((prev) => ({ ...prev, numbering: value })),
                },
                {
                  label: "页脚页码",
                  checked: pageNumbers,
                  onChange: (value: boolean) => setOverrides((prev) => ({ ...prev, pageNumbers: value })),
                },
              ].map((item) => (
                <label key={item.label} className="flex cursor-pointer items-center gap-2.5 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={item.checked}
                    onChange={(event) => item.onChange(event.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  />
                  {item.label}
                </label>
              ))}
            </div>
            <label className="mt-4 block">
              <span className="text-xs font-medium text-slate-500">文档标题</span>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
              />
            </label>
          </div>

          <div className="space-y-2">
            <button
              type="button"
              onClick={runExport}
              disabled={exporting}
              className="w-full rounded-xl bg-gradient-to-r from-sky-600 to-cyan-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-sky-500/25 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
            >
              {exporting ? "正在生成…" : "导出 Word 文档"}
            </button>
            <button
              type="button"
              onClick={runReferences}
              disabled={refLoading}
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {refLoading ? "AI 正在整理文献…" : "AI 规范化参考文献"}
            </button>
          </div>

          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
          )}
        </section>
      </div>

      {refResult && (
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-bold text-slate-800">参考文献规范化结果</h2>
          {!refResult.found ? (
            <p className="mt-3 text-sm text-slate-500">{refResult.notes.join("；")}</p>
          ) : (
            <>
              <ul className="mt-3 space-y-2">
                {refResult.entries.map((entry) => (
                  <li key={entry.index} className="rounded-xl border border-slate-200 p-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-slate-400">[{entry.index}]</span>
                      <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">{entry.type}</span>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-slate-800">{entry.formatted}</p>
                    {entry.note && <p className="mt-1 text-xs text-amber-700">{entry.note}</p>}
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-slate-400">原文已同步更新，可直接导出。</p>
            </>
          )}
        </section>
      )}

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-5 py-3">
          <h2 className="text-sm font-bold text-slate-800">排版预览</h2>
        </div>
        <div className="max-h-[30rem] overflow-y-auto px-6 py-5">
          {markdown.trim() ? (
            <MarkdownPreview markdown={markdown} />
          ) : (
            <p className="text-sm text-slate-400">左侧填写内容后，这里显示预览。</p>
          )}
        </div>
      </section>
    </main>
  );
}
