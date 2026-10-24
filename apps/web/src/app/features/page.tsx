import type { Metadata } from "next";
import Link from "next/link";

import { FeatureCard } from "@/components/FeatureCard";
import { Icon } from "@/components/Icons";
import { FEATURES } from "@/lib/features";

export const metadata: Metadata = {
  title: "功能分区",
  description: "大肥鱼小组工作台的七个功能模块总览。",
};

const LAYERS = [
  {
    title: "文档层",
    desc: "导入、解析、结构化表示（IR）",
    items: ["docx / Markdown 解析", "章节树与题注识别", "版本快照与回滚"],
  },
  {
    title: "AI 能力层",
    desc: "统一的大模型网关与提示词库",
    items: ["多厂商可切换", "流式输出", "结构化 JSON 输出"],
  },
  {
    title: "检索层",
    desc: "联网搜索与学术元数据",
    items: ["OpenAlex / Crossref", "网页搜索兜底", "来源溯源记录"],
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
          七个模块按实施顺序编号（F1–F7），每个模块对应一个独立的入口页面。
          七个模块均已上线，点进去即可使用。
        </p>
      </header>

      <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((feature, index) => (
          <FeatureCard key={feature.slug} feature={feature} index={index} />
        ))}
      </div>

      <section className="mt-16">
        <h2 className="text-xl font-bold text-slate-900">支撑这三层能力</h2>
        <p className="mt-2 text-sm text-slate-500">
          七个功能不是七个孤立的小工具，它们共用同一套底层能力。
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