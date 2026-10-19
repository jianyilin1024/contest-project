import { ApiStatus } from "@/components/ApiStatus";

const FEATURES = [
  {
    tag: "F1",
    title: "多部分整合",
    desc: "汇总成员各自负责的章节，自动归一标题层级、标记重复内容与冲突点。",
  },
  {
    tag: "F2",
    title: "分工记录",
    desc: "任务看板记录谁负责哪一节、进度与截止时间，并统计贡献度。",
  },
  {
    tag: "F3",
    title: "过渡段落生成",
    desc: "为相邻章节补写衔接文字，让拼接处读起来是同一篇文章。",
  },
  {
    tag: "F4",
    title: "用语风格统一",
    desc: "提取风格基准，逐段改写并给出 diff，术语表全篇统一。",
  },
  {
    tag: "F5",
    title: "AI 辅助排版",
    desc: "套用模板生成规范文稿：标题层级、目录页码、参考文献格式。",
  },
  {
    tag: "F6",
    title: "数据助手",
    desc: "识别段落中的数据缺口，检索并给出带来源的可核实数据。",
  },
  {
    tag: "F7",
    title: "参考文献助手",
    desc: "按概要检索真实文献，去重并生成 GB/T 7714 引用条目。",
  },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-14">
      <header>
        <p className="text-sm font-medium tracking-wide text-indigo-600">
          参赛项目 · 工程骨架 v0.1
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          AI 赋能的小组作业与论文协作台
        </h1>
        <p className="mt-4 max-w-3xl text-base leading-relaxed text-slate-600">
          把多人分头写的作业与论文，合成一篇风格统一、格式规范、引用可靠的成品。
          当前仓库处于基础框架阶段，功能模块将按计划逐步接入。
        </p>
      </header>

      <section className="mt-8 grid gap-4 sm:grid-cols-2">
        <ApiStatus />
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-medium text-slate-700">接口文档</div>
          <div className="mt-2 text-sm text-slate-500">
            <a
              className="text-indigo-600 underline-offset-2 hover:underline"
              href="http://localhost:8000/docs"
            >
              /docs
            </a>
            {" · "}
            <a
              className="text-indigo-600 underline-offset-2 hover:underline"
              href="http://localhost:8000/redoc"
            >
              /redoc
            </a>
            {" · 就绪探针 /api/v1/health/ready"}
          </div>
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-lg font-semibold text-slate-800">功能规划</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <article
              key={feature.tag}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-300 hover:shadow"
            >
              <span className="inline-flex rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                {feature.tag}
              </span>
              <h3 className="mt-3 text-base font-semibold text-slate-900">
                {feature.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">
                {feature.desc}
              </p>
            </article>
          ))}
        </div>
      </section>

      <footer className="mt-14 border-t border-slate-200 pt-6 text-sm text-slate-500">
        详细方案见仓库 <code className="rounded bg-slate-100 px-1">docs/</code>{" "}
        目录；环境变量说明见{" "}
        <code className="rounded bg-slate-100 px-1">docs/环境配置说明.md</code>。
      </footer>
    </main>
  );
}
