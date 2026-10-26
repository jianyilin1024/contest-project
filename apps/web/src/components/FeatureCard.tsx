import Link from "next/link";

import { Icon } from "@/components/Icons";
import { STATUS_LABEL, type Feature } from "@/lib/features";

const STATUS_STYLE: Record<Feature["status"], string> = {
  planned: "bg-slate-100 text-slate-600",
  building: "bg-amber-100 text-amber-700",
  done: "bg-emerald-100 text-emerald-700",
};

/** 功能卡片：图标、编号、状态徽标、一句话说明，点击进入对应功能页。 */
export function FeatureCard({ feature, index = 0 }: { feature: Feature; index?: number }) {
  return (
    <Link
      href={`/features/${feature.slug}`}
      style={{ animationDelay: `${index * 55}ms` }}
      className="card-lift animate-fade-up group relative flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex items-start justify-between">
        <div
          className={`inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${feature.accent} text-white shadow-md shadow-indigo-500/20`}
        >
          <Icon name={feature.icon} className="h-5 w-5" />
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-slate-900/5 px-1.5 py-0.5 text-[11px] font-bold text-slate-500">
            {feature.code}
          </span>
          <span
            className={`rounded-md px-1.5 py-0.5 text-[11px] font-medium ${STATUS_STYLE[feature.status]}`}
          >
            {STATUS_LABEL[feature.status]}
          </span>
        </div>
      </div>

      <h3 className="mt-4 text-base font-bold text-slate-900">{feature.title}</h3>
      <p className="mt-1.5 flex-1 text-sm leading-relaxed text-slate-500">
        {feature.tagline}
      </p>

      <div className="mt-4 flex items-center justify-end border-t border-slate-100 pt-3">
        <span className="inline-flex items-center gap-1 text-sm font-semibold text-brand-600 transition group-hover:gap-2">
          进入模块
          <Icon name="arrowRight" className="h-3.5 w-3.5" />
        </span>
      </div>
    </Link>
  );
}
