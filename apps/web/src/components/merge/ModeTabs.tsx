import Link from "next/link";

import { Icon } from "@/components/Icons";

export type MergeMode = "multi" | "single" | "transition" | "style";

const TABS: { key: MergeMode; href: string; label: string; hint: string; icon: "layers" | "wand" | "link" | "type" }[] = [
  {
    key: "multi",
    href: "/features/merge",
    label: "多部分整合",
    hint: "多人各写一部分，合成一份",
    icon: "layers",
  },
  {
    key: "single",
    href: "/features/merge/analyze",
    label: "单文档分析",
    hint: "一篇文档，判断是否多人执笔",
    icon: "wand",
  },
  {
    key: "transition",
    href: "/features/merge/transition",
    label: "过渡段落",
    hint: "在章节拼接处补写衔接",
    icon: "link",
  },
  {
    key: "style",
    href: "/features/merge/style",
    label: "风格统一",
    hint: "逐段改写为统一书面语",
    icon: "type",
  },
];

/** 多部分整合模块的四个页签：整合 / 单文档分析 / 过渡 / 风格。 */
export function ModeTabs({ active }: { active: MergeMode }) {
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
                ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            <Icon name={tab.icon} className="h-4 w-4 shrink-0" />
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold">{tab.label}</span>
              <span
                className={`block truncate text-[11px] ${isActive ? "text-indigo-100" : "text-slate-400"}`}
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
