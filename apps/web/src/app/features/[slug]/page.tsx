import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Icon } from "@/components/Icons";
import { FEATURES, FEATURE_MAP, STATUS_LABEL } from "@/lib/features";

type PageProps = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return FEATURES.map((feature) => ({ slug: feature.slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const feature = FEATURE_MAP[slug];
  if (!feature) return { title: "功能未找到" };
  return { title: feature.title, description: feature.tagline };
}

export default async function FeatureDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const feature = FEATURE_MAP[slug];
  if (!feature) notFound();

  const index = FEATURES.findIndex((item) => item.slug === feature.slug);
  const prev = index > 0 ? FEATURES[index - 1] : null;
  const next = index < FEATURES.length - 1 ? FEATURES[index + 1] : null;

  return (
    <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">
          首页
        </Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features" className="transition hover:text-brand-600">
          功能分区
        </Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">{feature.title}</span>
      </nav>

      <div className="mt-6 grid gap-10 lg:grid-cols-[1fr_15rem]">
        {/* ---------------- 主内容 ---------------- */}
        <div>
          <header className="flex flex-wrap items-start gap-5">
            <div
              className={`inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br ${feature.accent} text-white shadow-lg shadow-indigo-500/25`}
            >
              <Icon name={feature.icon} className="h-7 w-7" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-slate-900/5 px-2 py-0.5 text-xs font-bold text-slate-500">
                  {feature.code}
                </span>
                <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                  {STATUS_LABEL[feature.status]}
                </span>
                <span className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                  {feature.stage} 阶段
                </span>
              </div>
              <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">
                {feature.title}
              </h1>
              <p className="mt-2 text-sm text-slate-500">{feature.tagline}</p>
            </div>
          </header>

          <p className="mt-7 text-[15px] leading-8 text-slate-700">{feature.description}</p>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-slate-400 uppercase">
                <Icon name="arrowRight" className="h-3.5 w-3.5" />
                输入
              </div>
              <p className="mt-2 text-sm text-slate-700">{feature.input}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-slate-400 uppercase">
                <Icon name="check" className="h-3.5 w-3.5" />
                输出
              </div>
              <p className="mt-2 text-sm text-slate-700">{feature.output}</p>
            </div>
          </div>

          <section className="mt-10">
            <h2 className="text-lg font-bold text-slate-900">计划具备的能力</h2>
            <ul className="mt-4 space-y-3">
              {feature.capabilities.map((capability) => (
                <li
                  key={capability}
                  className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <span
                    className={`mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-gradient-to-br ${feature.accent} text-white`}
                  >
                    <Icon name="check" className="h-3 w-3" />
                  </span>
                  <span className="text-sm leading-relaxed text-slate-700">{capability}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* 占位工作区 */}
          <section className="mt-10">
            <h2 className="text-lg font-bold text-slate-900">工作区</h2>
            <div className="mt-4 rounded-2xl border-2 border-dashed border-slate-300 bg-white/60 p-10 text-center">
              <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                <Icon name="clock" className="h-5 w-5" />
              </div>
              <p className="mt-4 text-sm font-semibold text-slate-700">
                该模块正在开发中
              </p>
              <p className="mx-auto mt-2 max-w-md text-xs leading-relaxed text-slate-500">
                计划在 {feature.stage} 阶段交付。当前仓库已完成工程骨架，
                接口与数据结构就绪后此处将替换为可操作的界面。
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-3">
                <Link
                  href="/features"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400"
                >
                  <Icon name="grid" className="h-3.5 w-3.5" />
                  返回功能总览
                </Link>
                <a
                  href="https://github.com/jianyilin1024/contest-project"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400"
                >
                  <Icon name="github" className="h-3.5 w-3.5" />
                  查看开发进度
                </a>
              </div>
            </div>
          </section>

          {/* 上一个 / 下一个 */}
          <nav className="mt-10 grid gap-4 sm:grid-cols-2">
            {prev ? (
              <Link
                href={`/features/${prev.slug}`}
                className="card-lift group rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
              >
                <span className="text-xs text-slate-400">上一个 · {prev.code}</span>
                <span className="mt-1 flex items-center gap-2 text-sm font-semibold text-slate-800">
                  <Icon name="arrowRight" className="h-3.5 w-3.5 rotate-180 text-slate-400" />
                  {prev.title}
                </span>
              </Link>
            ) : (
              <span />
            )}
            {next && (
              <Link
                href={`/features/${next.slug}`}
                className="card-lift group rounded-2xl border border-slate-200 bg-white p-4 text-right shadow-sm sm:col-start-2"
              >
                <span className="text-xs text-slate-400">下一个 · {next.code}</span>
                <span className="mt-1 flex items-center justify-end gap-2 text-sm font-semibold text-slate-800">
                  {next.title}
                  <Icon name="arrowRight" className="h-3.5 w-3.5 text-slate-400" />
                </span>
              </Link>
            )}
          </nav>
        </div>

        {/* ---------------- 侧边导航 ---------------- */}
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <h2 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
            全部功能
          </h2>
          <ul className="mt-3 space-y-1.5">
            {FEATURES.map((item) => {
              const active = item.slug === feature.slug;
              return (
                <li key={item.slug}>
                  <Link
                    href={`/features/${item.slug}`}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition ${
                      active
                        ? "bg-white font-semibold text-brand-700 shadow-sm ring-1 ring-brand-100"
                        : "text-slate-600 hover:bg-white/70 hover:text-slate-900"
                    }`}
                  >
                    <span
                      className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-white ${
                        active ? `bg-gradient-to-br ${item.accent}` : "bg-slate-300"
                      }`}
                    >
                      <Icon name={item.icon} className="h-3.5 w-3.5" />
                    </span>
                    <span className="min-w-0 flex-1 truncate">{item.title}</span>
                    <span className="text-[10px] font-bold text-slate-400">{item.code}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </aside>
      </div>
    </main>
  );
}
