import Link from "next/link";

import { Icon } from "@/components/Icons";

export type CitationMode = "suggest" | "search" | "data";

const TABS: { key: CitationMode; href: string; label: string; hint: string; icon: "book" | "search" | "database" }[] = [
  {
    key: "suggest",
    href: "/features/citations",
    label: "引用建议",
    hint: "读你的论文，指出哪里该补引用",
    icon: "book",
  },
  {
    key: "search",
    href: "/features/citations/search",
    label: "文献检索",
    hint: "按关键词找文献，导出引用格式",
    icon: "search",
  },
  {
    key: "data",
    href: "/features/citations/data",
    label: "数据补全",
    hint: "找出缺数据的地方并给来源",
    icon: "database",
  },
];

/** 引用助手模块的三个页签：引用建议 / 文献检索 / 数据补全。 */
export function CitationTabs({ active }: { active: CitationMode }) {
  return (
    <div className="mt-5 flex flex-wrap gap-1.5 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-sm">
      {TABS.map((tab) => {
        const isActive = tab.key === active;
        return (
          <Link
            key={tab.key}
            href={tab.href}
            aria-current={isActive ? "page" : undefined}
            className={`flex min-w-0 flex-1 basis-40 items-center gap-2.5 rounded-xl px-3 py-2 transition ${
              isActive
                ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            <Icon name={tab.icon} className="h-4 w-4 shrink-0" />
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold">{tab.label}</span>
              <span
                className={`block truncate text-[11px] ${isActive ? "text-violet-100" : "text-slate-400"}`}
              >
                {tab.hint}
              </span>
            </span>
          </Link>
        );
      })}
    </div>
  );
}
