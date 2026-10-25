import Link from "next/link";

import { Icon } from "@/components/Icons";

const TABS = [
  {
    key: "multi",
    href: "/features/merge",
    label: "多文档整合",
    hint: "多人各写一部分，合成一份",
    icon: "layers" as const,
  },
  {
    key: "single",
    href: "/features/merge/analyze",
    label: "单文档 AI 分析",
    hint: "一篇文档，判断是否多人执笔",
    icon: "wand" as const,
  },
];

/** 整合模块的两个页签：多部分整合 / 单文档分析。 */
export function ModeTabs({ active }: { active: "multi" | "single" }) {
  return (
    <div className="mt-5 flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-sm">
      {TABS.map((tab) => {
        const isActive = tab.key === active;
        return (
          <Link
            key={tab.key}
            href={tab.href}
            aria-current={isActive ? "page" : undefined}
            className={`flex flex-1 items-center gap-3 rounded-xl px-4 py-2.5 transition ${
              isActive
                ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            <Icon name={tab.icon} className="h-4 w-4 shrink-0" />
            <span className="min-w-0">
              <span className="block text-sm font-semibold">{tab.label}</span>
              <span className={`block truncate text-xs ${isActive ? "text-indigo-100" : "text-slate-400"}`}>
                {tab.hint}
              </span>
            </span>
          </Link>
        );
      })}
    </div>
  );
}
