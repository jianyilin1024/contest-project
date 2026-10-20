"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icons";
import {
  API_BASE_LABEL,
  fetchHealth,
  fetchLLMHealth,
  type HealthResponse,
  type LLMHealthResponse,
} from "@/lib/api";

type State<T> =
  | { kind: "loading" }
  | { kind: "ok"; data: T }
  | { kind: "error"; message: string };

type Tone = { dot: string; text: string; label: string };

const TONES: Record<State<unknown>["kind"], Tone> = {
  loading: { dot: "bg-amber-400", text: "text-amber-700", label: "检测中" },
  ok: { dot: "bg-emerald-500", text: "text-emerald-700", label: "服务正常" },
  error: { dot: "bg-rose-500", text: "text-rose-700", label: "连接失败" },
};

function useHealth<T>(loader: (signal: AbortSignal) => Promise<T>): State<T> {
  const [state, setState] = useState<State<T>>({ kind: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    loader(controller.signal)
      .then((data) => setState({ kind: "ok", data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          kind: "error",
          message: error instanceof Error ? error.message : "未知错误",
        });
      });
    return () => controller.abort();
    // loader 是模块级稳定函数，无需加入依赖
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return state;
}

function StatusRow({
  icon,
  title,
  state,
  tone,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  state: State<unknown>;
  tone: Tone;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="rounded-xl bg-slate-100 p-2 text-slate-500">{icon}</div>
      <div className="min-w-0 flex-1 text-sm">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-slate-800">{title}</span>
          <span className="inline-flex shrink-0 items-center gap-1.5">
            <span
              className={`h-1.5 w-1.5 rounded-full ${tone.dot} ${
                state.kind === "ok" ? "pulse-ring" : ""
              }`}
            />
            <span className={`text-xs font-semibold ${tone.text}`}>{tone.label}</span>
          </span>
        </div>
        <div className="mt-0.5 text-xs text-slate-500">{children}</div>
      </div>
    </div>
  );
}

export function ApiStatus() {
  const backend = useHealth<HealthResponse>(fetchHealth);
  const llm = useHealth<LLMHealthResponse>(fetchLLMHealth);

  const aiTone: Tone =
    llm.kind === "ok" && llm.data.status !== "ok"
      ? { dot: "bg-rose-500", text: "text-rose-700", label: "未就绪" }
      : TONES[llm.kind];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
          运行状态
        </span>
      </div>

      <div className="mt-4 space-y-4">
        <StatusRow
          icon={<Icon name="sparkles" className="h-4 w-4" />}
          title="后端服务"
          state={backend}
          tone={TONES[backend.kind]}
        >
          {backend.kind === "loading" && "正在连接…"}
          {backend.kind === "ok" &&
            `${backend.data.app} · 环境 ${backend.data.env} · v${backend.data.version}`}
          {backend.kind === "error" && `${backend.message} · ${API_BASE_LABEL}`}
        </StatusRow>

        <StatusRow
          icon={<Icon name="wand" className="h-4 w-4" />}
          title="AI 能力"
          state={llm}
          tone={aiTone}
        >
          {llm.kind === "loading" && "正在检测模型连通性…"}
          {llm.kind === "ok" && llm.data.status === "ok" && (
            <>
              默认 {llm.data.default_model}
              {llm.data.models.length > 0 && ` · 可用 ${llm.data.models.length} 个模型`}
            </>
          )}
          {llm.kind === "ok" && llm.data.status !== "ok" && (
            <>{llm.data.detail ?? "模型服务不可用"}</>
          )}
          {llm.kind === "error" && llm.message}
        </StatusRow>
      </div>
    </div>
  );
}
