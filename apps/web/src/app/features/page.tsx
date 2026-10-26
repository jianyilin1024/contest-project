import type { Metadata } from "next";
import Link from "next/link";

import { FeatureCard } from "@/components/FeatureCard";
import { Icon } from "@/components/Icons";
import { FEATURES } from "@/lib/features";

export const metadata: Metadata = {
  title: "功能分区",
  description: "大肥鱼小组工作台的四个功能模块总览。",
};

const LAYERS = [
  {
    title: "文档层",
    desc: "导入、解析、结构化表示（IR）",
    items: ["docx / Markdown / 纯文本解析", "标题层级与编号归一", "重复段落与术语冲突检测"],
  },
  {
    title: "AI 能力层",
    desc: "统一的大模型网关与提示词库",
    items: ["结构化 JSON 输出（截断重试）", "推理模型与流式输出", "失败降级，不阻断主流程"],
  },
  {
    title: "检索层",
    desc: "联网搜索与学术元数据",
    items: ["OpenAlex / Crossref / Open Library", "联网搜索（DeepSeek）", "来源白名单校验"],
  },
];

export default function FeaturesPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <nav className="flex items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">
          首页
        </Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">功能分区</span>
      </nav>

      <header className="mt-6">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">功能分区</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600">
          四个模块各对应一组页面：多部分整合下含过渡与风格统一，引用助手下含文献检索与数据补全。
        </p>
      </header>

      <section className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-indigo-200 bg-gradient-to-r from-indigo-50 to-violet-50 p-5">
        <div className="min-w-0">
          <p className="text-sm font-bold text-slate-900">不想逐个模块走一遍？</p>
          <p className="mt-1 text-sm text-slate-600">
            一键成稿会把「合并 → 过渡 → 文献 → 排版」串成一步，完成后直接下载 Word。
          </p>
        </div>
        <Link
          href="/oneclick"
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-0.5"
        >
          <Icon name="sparkles" className="h-4 w-4" />
          一键成稿
        </Link>
      </section>

      <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((feature, index) => (
          <FeatureCard key={feature.slug} feature={feature} index={index} />
        ))}
      </div>

      <section className="mt-16">
        <h2 className="text-xl font-bold text-slate-900">支撑这三层能力</h2>
        <p className="mt-2 text-sm text-slate-500">
          四个模块不是四套独立实现，它们共用同一套底层能力。
        </p>
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          {LAYERS.map((layer) => (
            <div
              key={layer.title}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <h3 className="text-sm font-bold text-slate-900">{layer.title}</h3>
              <p className="mt-1 text-xs text-slate-500">{layer.desc}</p>
              <ul className="mt-4 space-y-2">
                {layer.items.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-sm text-slate-600">
                    <Icon name="check" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}