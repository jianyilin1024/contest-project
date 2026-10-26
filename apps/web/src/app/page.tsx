import Link from "next/link";

import { ApiStatus } from "@/components/ApiStatus";
import { FeatureCard } from "@/components/FeatureCard";
import { Icon } from "@/components/Icons";
import { Logo } from "@/components/Logo";
import { FEATURES } from "@/lib/features";

const FLOW = [
  { step: "01", title: "各自写作", desc: "成员认领章节，各自提交", icon: "checkSquare" as const },
  { step: "02", title: "一键整合", desc: "归一结构、标记冲突", icon: "layers" as const },
  { step: "03", title: "统一风格", desc: "过渡衔接 + 逐段改写", icon: "wand" as const },
  { step: "04", title: "规范导出", desc: "排版 + 引用一键成稿", icon: "layout" as const },
];

const STATS = [
  { value: "4", label: "功能模块" },
  { value: "3", label: "底层能力层" },
  { value: "1", label: "条主链路" },
  { value: "0", label: "元起步成本" },
];

/**
 * 首页：一句话定位 + 一键成稿主推 + 模块入口。
 *
 * 纯静态渲染、不请求后端——首页必须在后端异常时也能正常打开。
 */
export default function HomePage() {
  return (
    <main>
      {/* ================= Hero ================= */}
      <section className="relative overflow-hidden">
        <div className="grid-pattern pointer-events-none absolute inset-0 opacity-40" />
        <div className="pointer-events-none absolute -top-24 left-1/2 h-72 w-[46rem] -translate-x-1/2 rounded-full bg-gradient-to-r from-indigo-300/40 via-violet-300/40 to-cyan-300/40 blur-3xl" />

        <div className="relative mx-auto grid max-w-6xl gap-12 px-4 pt-16 pb-20 sm:px-6 lg:grid-cols-[1.35fr_1fr] lg:items-center lg:pt-24">
          <div className="animate-fade-up">
            <span className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-white/70 px-3 py-1 text-xs font-medium text-indigo-700 shadow-sm backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
              四大模块全部上线 · 已部署至线上环境
            </span>

            <h1 className="mt-6 text-4xl leading-tight font-extrabold tracking-tight sm:text-5xl">
              <span className="text-gradient">大肥鱼小组工作台</span>
            </h1>

            <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-600">
              把多人分头写的作业与论文，合成一篇
              <strong className="font-semibold text-slate-800">风格统一</strong>、
              <strong className="font-semibold text-slate-800">格式规范</strong>、
              <strong className="font-semibold text-slate-800">引用可靠</strong>
              的成品。
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                href="/oneclick"
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 via-violet-600 to-cyan-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-indigo-500/30"
              >
                <Icon name="sparkles" className="h-4 w-4" />
                一键成稿
              </Link>
              <Link
                href="/features/merge"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-slate-400"
              >
                <Icon name="layers" className="h-4 w-4" />
                开始整合文稿
              </Link>
              <Link
                href="/features"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-slate-400"
              >
                <Icon name="grid" className="h-4 w-4" />
                浏览全部功能
              </Link>
            </div>

            <dl className="mt-10 grid max-w-xl grid-cols-2 gap-4 sm:grid-cols-4">
              {STATS.map((stat) => (
                <div key={stat.label} className="rounded-xl border border-slate-200 bg-white/70 p-3 backdrop-blur">
                  <dt className="text-2xl font-extrabold text-slate-900">{stat.value}</dt>
                  <dd className="mt-0.5 text-xs text-slate-500">{stat.label}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="animate-fade-up [animation-delay:150ms]">
            <div className="animate-floaty rounded-3xl border border-slate-200 bg-white/80 p-6 shadow-xl shadow-indigo-500/10 backdrop-blur">
              <div className="flex items-center gap-3">
                <Logo className="h-12 w-12" id="hero" />
                <div>
                  <p className="text-sm font-bold text-slate-900">协作工作台</p>
                  <p className="text-xs text-slate-500">一站式小组作业流水线</p>
                </div>
              </div>

              <div className="mt-5 space-y-2.5">
                {FEATURES.slice(0, 3).map((feature) => (
                  <Link
                    key={feature.slug}
                    href={`/features/${feature.slug}`}
                    className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5 transition hover:border-indigo-300 hover:bg-indigo-50/40"
                  >
                    <span
                      className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${feature.accent} text-white`}
                    >
                      <Icon name={feature.icon} className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-slate-800">
                        {feature.title}
                      </span>
                      <span className="block truncate text-xs text-slate-500">
                        {feature.tagline}
                      </span>
                    </span>
                    <Icon name="chevronRight" className="h-4 w-4 shrink-0 text-slate-400" />
                  </Link>
                ))}
              </div>

              <div className="mt-4">
                <ApiStatus />
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* ================= 主链路 ================= */}
      <section className="mx-auto mt-20 max-w-6xl px-4 sm:px-6">
        <div className="rounded-3xl border border-slate-200 bg-white/80 p-8 shadow-sm backdrop-blur">
          <h2 className="text-xl font-bold text-slate-900">主链路：从分工到成稿</h2>
          <p className="mt-2 text-sm text-slate-500">
            这条闭环已经能完整讲出「四人分头写 → 合成一篇规范论文」的整个过程。
          </p>

          <ol className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FLOW.map((item, index) => (
              <li key={item.step} className="relative">
                <div className="rounded-2xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-5">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                      <Icon name={item.icon} className="h-4 w-4" />
                    </span>
                    <span className="text-xs font-bold text-slate-300">{item.step}</span>
                  </div>
                  <h3 className="mt-3 text-sm font-bold text-slate-800">{item.title}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">{item.desc}</p>
                </div>
                {index < FLOW.length - 1 && (
                  <Icon
                    name="arrowRight"
                    className="absolute top-1/2 -right-3 hidden h-5 w-5 -translate-y-1/2 text-slate-300 lg:block"
                  />
                )}
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ================= 结尾 CTA ================= */}
      <section className="mx-auto mt-20 max-w-6xl px-4 sm:px-6">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-600 via-violet-600 to-cyan-600 p-10 text-center shadow-xl">
          <div className="grid-pattern absolute inset-0 opacity-20" />
          <div className="relative">
            <h2 className="text-2xl font-bold text-white sm:text-3xl">
              现在就开始你的第一次协作
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-indigo-50">
              从「多部分整合」进入，上传各成员的分部文稿，体验从散乱到成稿的全过程。
            </p>
            <div className="mt-7 flex flex-wrap justify-center gap-3">
              <Link
                href="/features/merge"
                className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-indigo-700 shadow-lg transition hover:-translate-y-0.5"
              >
                <Icon name="layers" className="h-4 w-4" />
                进入多部分整合
              </Link>
              <Link
                href="/about"
                className="inline-flex items-center gap-2 rounded-xl border border-white/40 bg-white/10 px-5 py-3 text-sm font-semibold text-white backdrop-blur transition hover:-translate-y-0.5 hover:bg-white/20"
              >
                <Icon name="info" className="h-4 w-4" />
                了解项目
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
