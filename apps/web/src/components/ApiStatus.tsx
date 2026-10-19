"use client";

import { useEffect, useState } from "react";

import { API_BASE_URL, fetchHealth, type HealthResponse } from "@/lib/api";

type State =
  | { kind: "loading" }
  | { kind: "ok"; data: HealthResponse }
  | { kind: "error"; message: string };

export function ApiStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((data) => setState({ kind: "ok", data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          kind: "error",
          message: error instanceof Error ? error.message : "未知错误",
        });
      });
    return () => controller.abort();
  }, []);

  const dot =
    state.kind === "ok"
      ? "bg-emerald-500"
      : state.kind === "error"
        ? "bg-rose-500"
        : "bg-amber-400";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
        <span className="text-sm font-medium text-slate-700">后端连接状态</span>
      </div>
      <div className="mt-2 text-sm text-slate-500">
        {state.kind === "loading" && "正在连接后端…"}
        {state.kind === "ok" && (
          <>
            {state.data.app} · {state.data.env} · v{state.data.version}
          </>
        )}
        {state.kind === "error" && (
          <>
            连接失败：{state.message}
            <span className="mt-1 block text-xs text-slate-400">
              请确认后端已启动（{API_BASE_URL}）
            </span>
          </>
        )}
      </div>
    </div>
  );
}
