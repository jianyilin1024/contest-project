"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icons";
import {
  addMember,
  createProject,
  createTask,
  deleteProject,
  deleteTask,
  getProject,
  listProjects,
  removeMember,
  updateTask,
  type Project,
  type ProjectBrief,
  type Task,
} from "@/lib/api";

const COLUMNS: { key: Task["status"]; label: string; tone: string }[] = [
  { key: "todo", label: "待办", tone: "border-slate-300" },
  { key: "doing", label: "进行中", tone: "border-amber-300" },
  { key: "done", label: "已完成", tone: "border-emerald-300" },
];

/**
 * 分工记录看板：项目 / 成员 / 任务三列。
 *
 * 每次写操作后都重新拉取项目详情，而不是在本地拼状态——
 * 删除成员会把任务的 member_id 置空，本地拼接容易与服务端不一致。
 */
export default function TasksPage() {
  const [projects, setProjects] = useState<ProjectBrief[]>([]);
  const [current, setCurrent] = useState<Project | null>(null);
  const [newProject, setNewProject] = useState("");
  const [newMember, setNewMember] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [taskMember, setTaskMember] = useState<number | "">("");
  const [taskDue, setTaskDue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refreshList = async () => {
    try {
      setProjects(await listProjects());
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    }
  };

  const open = async (id: number) => {
    try {
      setCurrent(await getProject(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    }
  };

  useEffect(() => {
    // 首次进入拉取项目列表；setState 发生在 await 之后，属于正常的异步加载
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshList();
  }, []);

  const run = async (fn: () => Promise<void>) => {
    setLoading(true);
    setError("");
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setLoading(false);
    }
  };

  const projectId = current?.id ?? 0;

  return (
    <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link href="/" className="transition hover:text-brand-600">首页</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <Link href="/features" className="transition hover:text-brand-600">功能分区</Link>
        <Icon name="chevronRight" className="h-3 w-3" />
        <span className="font-medium text-slate-700">分工记录</span>
      </nav>

      <header className="mt-6 flex flex-wrap items-start gap-5">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-500 text-white shadow-lg shadow-emerald-500/25">
          <Icon name="checkSquare" className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-900/5 px-2 py-0.5 text-xs font-bold text-slate-500">F2</span>
            <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">可用</span>
          </div>
          <h1 className="mt-2.5 text-3xl font-extrabold tracking-tight text-slate-900">分工记录</h1>
          <p className="mt-2 text-sm text-slate-500">
            建项目、拉成员、派任务，用看板跟踪谁负责哪一节、进度如何、什么时候交。
          </p>
        </div>
      </header>

      {error && (
        <div className="mt-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[16rem_1fr]">
        {/* 项目列表 */}
        <aside className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-bold text-slate-800">项目</h2>
          <div className="mt-3 flex gap-2">
            <input
              value={newProject}
              onChange={(event) => setNewProject(event.target.value)}
              placeholder="新项目名"
              className="min-w-0 flex-1 rounded-lg border border-slate-300 px-2 py-1.5 text-sm outline-none focus:border-emerald-400"
            />
            <button
              type="button"
              disabled={loading || !newProject.trim()}
              onClick={() =>
                run(async () => {
                  const project = await createProject(newProject.trim());
                  setNewProject("");
                  await refreshList();
                  setCurrent(project);
                })
              }
              className="rounded-lg bg-emerald-600 px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
            >
              新建
            </button>
          </div>
          <ul className="mt-3 space-y-1">
            {projects.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => void open(item.id)}
                  className={`w-full rounded-lg px-2.5 py-2 text-left text-sm transition ${
                    current?.id === item.id ? "bg-emerald-50 font-semibold text-emerald-700" : "text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  <span className="block truncate">{item.name}</span>
                  <span className="block text-xs text-slate-400">
                    {item.member_count} 人 · {item.done_count}/{item.task_count} 完成
                  </span>
                </button>
              </li>
            ))}
            {projects.length === 0 && <li className="text-xs text-slate-400">还没有项目，先建一个。</li>}
          </ul>
        </aside>

        {/* 看板 */}
        <section className="space-y-4">
          {!current ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
              选择或新建一个项目开始分工
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">{current.name}</h2>
                    <p className="text-xs text-slate-500">
                      待办 {current.stats.todo} · 进行中 {current.stats.doing} · 已完成 {current.stats.done}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      run(async () => {
                        await deleteProject(current.id);
                        setCurrent(null);
                        await refreshList();
                      })
                    }
                    className="rounded-lg border border-rose-200 px-2.5 py-1 text-xs text-rose-600 transition hover:bg-rose-50"
                  >
                    删除项目
                  </button>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <span className="text-xs text-slate-400">成员：</span>
                  {current.members.map((member) => (
                    <span
                      key={member.id}
                      className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
                    >
                      {member.name}
                      <button
                        type="button"
                        onClick={() =>
                          run(async () => {
                            await removeMember(member.id);
                            await open(projectId);
                            await refreshList();
                          })
                        }
                        className="text-slate-400 hover:text-rose-600"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <input
                    value={newMember}
                    onChange={(event) => setNewMember(event.target.value)}
                    placeholder="成员名"
                    className="w-24 rounded-lg border border-slate-300 px-2 py-1 text-xs outline-none focus:border-emerald-400"
                  />
                  <button
                    type="button"
                    disabled={!newMember.trim()}
                    onClick={() =>
                      run(async () => {
                        await addMember(projectId, newMember.trim());
                        setNewMember("");
                        await open(projectId);
                        await refreshList();
                      })
                    }
                    className="rounded-lg border border-slate-300 px-2 py-1 text-xs text-slate-700 disabled:opacity-50"
                  >
                    添加
                  </button>
                </div>

                <div className="mt-4 flex flex-wrap items-end gap-2 border-t border-slate-100 pt-3">
                  <input
                    value={taskTitle}
                    onChange={(event) => setTaskTitle(event.target.value)}
                    placeholder="任务（如：撰写第 2 章）"
                    className="min-w-0 flex-1 rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm outline-none focus:border-emerald-400"
                  />
                  <select
                    value={taskMember}
                    onChange={(event) => setTaskMember(event.target.value === "" ? "" : Number(event.target.value))}
                    className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                  >
                    <option value="">未指派</option>
                    {current.members.map((member) => (
                      <option key={member.id} value={member.id}>{member.name}</option>
                    ))}
                  </select>
                  <input
                    type="date"
                    value={taskDue}
                    onChange={(event) => setTaskDue(event.target.value)}
                    className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                  />
                  <button
                    type="button"
                    disabled={loading || !taskTitle.trim()}
                    onClick={() =>
                      run(async () => {
                        await createTask(projectId, {
                          title: taskTitle.trim(),
                          member_id: taskMember === "" ? null : taskMember,
                          due_date: taskDue || null,
                        });
                        setTaskTitle("");
                        setTaskDue("");
                        await open(projectId);
                        await refreshList();
                      })
                    }
                    className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
                  >
                    添加任务
                  </button>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                {COLUMNS.map((column) => {
                  const items = current.tasks.filter((task) => task.status === column.key);
                  return (
                    <div key={column.key} className={`rounded-2xl border-t-4 bg-white p-3 shadow-sm ${column.tone}`}>
                      <h3 className="flex items-center justify-between text-sm font-bold text-slate-700">
                        {column.label}
                        <span className="rounded-md bg-slate-100 px-1.5 text-xs text-slate-500">{items.length}</span>
                      </h3>
                      <ul className="mt-2 space-y-2">
                        {items.map((task) => (
                          <li key={task.id} className="rounded-xl border border-slate-200 p-2.5">
                            <p className="text-sm font-medium text-slate-800">{task.title}</p>
                            <p className="mt-1 text-xs text-slate-500">
                              {task.member_name || "未指派"}
                              {task.due_date ? ` · 截止 ${task.due_date}` : ""}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-1">
                              {COLUMNS.filter((item) => item.key !== task.status).map((item) => (
                                <button
                                  key={item.key}
                                  type="button"
                                  onClick={() =>
                                    run(async () => {
                                      await updateTask(task.id, { status: item.key });
                                      await open(projectId);
                                      await refreshList();
                                    })
                                  }
                                  className="rounded-md border border-slate-300 px-1.5 py-0.5 text-[11px] text-slate-600 transition hover:border-emerald-400"
                                >
                                  → {item.label}
                                </button>
                              ))}
                              <button
                                type="button"
                                onClick={() =>
                                  run(async () => {
                                    await deleteTask(task.id);
                                    await open(projectId);
                                    await refreshList();
                                  })
                                }
                                className="rounded-md px-1.5 py-0.5 text-[11px] text-slate-400 hover:text-rose-600"
                              >
                                删除
                              </button>
                            </div>
                          </li>
                        ))}
                        {items.length === 0 && <li className="py-3 text-center text-xs text-slate-300">空</li>}
                      </ul>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
