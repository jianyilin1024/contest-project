"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon, type IconName } from "@/components/Icons";
import { Logo } from "@/components/Logo";

const NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/", label: "首页", icon: "home" },
  { href: "/features", label: "功能分区", icon: "grid" },
  { href: "/about", label: "关于", icon: "info" },
];

/** 全站页头：品牌标识 + 主导航 + 进入工作台入口。 */
export function SiteHeader() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-6">
        <Link href="/" className="group flex items-center gap-2.5">
          <Logo className="h-9 w-9 transition-transform duration-300 group-hover:scale-110" id="header" />
          <span className="flex flex-col leading-tight">
            <span className="text-[15px] font-bold tracking-tight text-slate-900">
              大肥鱼小组工作台
            </span>
            <span className="hidden text-[11px] text-slate-500 sm:block">
              AI 协作写作 · 论文助手
            </span>
          </span>
        </Link>

        <nav className="ml-auto flex items-center gap-1">
          {NAV.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm font-medium transition ${
                  active
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <Icon name={item.icon} className="h-4 w-4 sm:hidden" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}

          <a
            href="https://github.com/jianyilin1024/contest-project"
            target="_blank"
            rel="noreferrer"
            title="查看源码"
            className="ml-1 rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <Icon name="github" className="h-4 w-4" />
          </a>

          <Link
            href="/features"
            className="ml-1 hidden rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition hover:from-indigo-500 hover:to-violet-500 sm:inline-flex"
          >
            进入工作台
          </Link>
        </nav>
      </div>
    </header>
  );
}
