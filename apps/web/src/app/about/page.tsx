import type { Metadata } from "next";
import Link from "next/link";

import { Icon } from "@/components/Icons";
import { Logo } from "@/components/Logo";

export const metadata: Metadata = {
  title: "关于项目",
  description: "大肥鱼小组工作台的项目定位、技术栈与实施路线。",
};

const STACK = [
  { name: "Next.js 16", role: "前端框架（App Router）" },
  { name: "React 19 + TypeScript", role: "界面与类型安全" },
  { name: "Tailwind CSS 4", role: "样式与设计系统" },
  { name: "FastAPI + Pydantic v2", role: "后端接口与校验" },
  { name: "PostgreSQL + pgvector", role: "业务数据与向量检索" },
  { name: "Redis", role: "缓存与异步任务队列" },
  { name: "Docker Compose + Nginx", role: "部署与反向代理" },
  { name: "OpenAlex / Crossref", role: "学术文献元数据" },
];

const ROADMAP = [
  { stage: "P0", title: "需求分析与实施计划", status: "done" },
  { stage: "P1", title: "工程骨架与首页设计", status: "done" },
  { stage: "P2", title: "数据模型 + 认证 + 项目/成员", status: "todo" },
  { stage: "P3", title: "文档导入与结构化解析", status: "todo" },
  { stage: "P4", title: "大模型网关", status: "todo" },
  { stage: "P5–P9", title: "F1 整合 → F5 排版（主链路）", status: "todo" },
  { stage: "P10–P11", title: "F6 数据助手 / F7 参考文献助手", status: "todo" },
  { stage: "P12", title: "联调、部署与演示材料", status: "todo" },
];

export default function AboutPage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <nav className="flex items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">
          首页
        </Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">关于</span>
      </nav>

      <header className="mt-8 flex items-center gap-4">
        <Logo className="h-14 w-14" id="about" />
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
            大肥鱼小组工作台
          </h1>
          <p className="mt-1 text-sm text-slate-500">AI 赋能的小组作业与论文协作台</p>
        </div>
      </header>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-bold text-slate-900">我们要解决什么</h2>
        <div className="mt-4 space-y-3 text-sm leading-relaxed text-slate-700">
          <p>
            小组作业的真实流程是：几个人分头写，最后拼在一起。结果往往是一篇文章里出现四种文风、
            两套术语、断裂的段落，以及来源不明的数据。
          </p>
          <p>
            本工作台把这条流水线产品化——从分工记录、文稿整合、过渡撰写、风格统一，
            到数据核实、文献检索与规范排版，每一环都由 AI 辅助完成，但
            <strong className="font-semibold text-slate-900">所有输出都必须可溯源、可回退</strong>。
          </p>
          <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800">
            <strong className="font-semibold">定位说明：</strong>
            本工具是写作辅助，不是代写。数据与文献一律附来源，改写一律留 diff，
            最终是否采用由使用者判断。
          </p>
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-bold text-slate-900">技术栈</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {STACK.map((item) => (
            <div
              key={item.name}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
            >
              <span className="text-sm font-semibold text-slate-800">{item.name}</span>
              <span className="text-xs text-slate-500">{item.role}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-bold text-slate-900">实施路线</h2>
        <ol className="mt-4 space-y-2">
          {ROADMAP.map((item) => (
            <li
              key={item.stage}
              className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
            >
              <span
                className={`inline-flex h-6 min-w-14 items-center justify-center rounded-md px-2 text-xs font-bold ${
                  item.status === "done"
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {item.stage}
              </span>
              <span className="flex-1 text-sm text-slate-700">{item.title}</span>
              {item.status === "done" ? (
                <Icon name="check" className="h-4 w-4 text-emerald-500" />
              ) : (
                <Icon name="clock" className="h-4 w-4 text-slate-300" />
              )}
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-bold text-slate-900">参与与反馈</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          项目源码公开在 GitHub，欢迎查看开发进度或提出建议。
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <a
            href="https://github.com/jianyilin1024/contest-project"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            <Icon name="github" className="h-4 w-4" />
            GitHub 仓库
          </a>
          <Link
            href="/features"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-400"
          >
            <Icon name="grid" className="h-4 w-4" />
            浏览功能分区
          </Link>
        </div>
      </section>
    </main>
  );
}
