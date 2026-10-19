import Link from "next/link";

import { Icon } from "@/components/Icons";
import { Logo } from "@/components/Logo";

export function SiteFooter() {
  return (
    <footer className="mt-20 border-t border-slate-200/80 bg-white/60 backdrop-blur">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <div className="flex items-center gap-2.5">
            <Logo className="h-8 w-8" id="footer" />
            <span className="text-sm font-bold text-slate-900">大肥鱼小组工作台</span>
          </div>
          <p className="mt-3 max-w-sm text-sm leading-relaxed text-slate-500">
            把多人分头写的作业与论文，合成一篇风格统一、格式规范、引用可靠的成品。
          </p>
          <p className="mt-3 text-xs text-slate-400">
            当前阶段：P1 工程骨架已就绪，功能模块开发中。
          </p>
        </div>

        <div>
          <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
            功能分区
          </h3>
          <ul className="mt-3 space-y-2 text-sm">
            {[
              { href: "/features/merge", label: "多部分整合" },
              { href: "/features/tasks", label: "分工记录" },
              { href: "/features/style", label: "用语风格统一" },
              { href: "/features/references", label: "参考文献助手" },
            ].map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="text-slate-600 transition hover:text-brand-700"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
            资源
          </h3>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <Link href="/features" className="text-slate-600 transition hover:text-brand-700">
                全部功能
              </Link>
            </li>
            <li>
              <Link href="/about" className="text-slate-600 transition hover:text-brand-700">
                关于项目
              </Link>
            </li>
            <li>
              <a
                href="https://github.com/jianyilin1024/contest-project"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-slate-600 transition hover:text-brand-700"
              >
                <Icon name="github" className="h-3.5 w-3.5" />
                源码仓库
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-slate-200/70 py-5 text-center text-xs text-slate-400">
        © {new Date().getFullYear()} 大肥鱼小组工作台 · 参赛项目
      </div>
    </footer>
  );
}
