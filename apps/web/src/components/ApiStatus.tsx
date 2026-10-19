"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icons";
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

  const tone =
    state.kind === "ok"
      ? { dot: "bg-emerald-500", text: "text-emerald-700", label: "服务正常" }
      : state.kind === "error"
        ? { dot: "bg-rose-500", text: "text-rose-700", label: "连接失败" }
        : { dot: "bg-amber-400", text: "text-amber-700", label: "检测中" };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
          运行状态
        </span>
        <span className="inline-flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${tone.dot} ${
              state.kind === "ok" ? "pulse-ring" : ""
            }`}
          />
          <span className={`text-xs font-semibold ${tone.text}`}>{tone.label}</span>
        </span>
      </div>

      <div className="mt-4 flex items-start gap-3">
        <div className="rounded-xl bg-slate-100 p-2 text-slate-500">
          <Icon name="sparkles" className="h-4 w-4" />
        </div>
        <div className="min-w-0 text-sm">
          {state.kind === "loading" && (
            <p className="text-slate-500">正在连接后端服务…</p>
          )}
          {state.kind === "ok" && (
            <>
              <p className="font-medium text-slate-800">{state.data.app}</p>
              <p className="mt-0.5 text-xs text-slate-500">
                环境 {state.data.env} · 版本 v{state.data.version}
              </p>
            </>
          )}
          {state.kind === "error" && (
            <>
              <p className="font-medium text-slate-800">后端未响应</p>
              <p className="mt-0.5 truncate text-xs text-slate-500">
                {state.message} · {API_BASE_URL}
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
