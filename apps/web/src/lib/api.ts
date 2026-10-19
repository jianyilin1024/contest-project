/** 后端接口地址与统一请求封装。 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type HealthResponse = {
  status: string;
  app: string;
  env: string;
  version: string;
};

export type LLMHealthResponse = {
  status: string;
  provider: string;
  base_url: string;
  default_model: string;
  models: string[];
  detail?: string | null;
};

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal, cache: "no-store" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return getJson<HealthResponse>("/api/v1/health", signal);
}

export function fetchLLMHealth(signal?: AbortSignal): Promise<LLMHealthResponse> {
  return getJson<LLMHealthResponse>("/api/v1/llm/health", signal);
}
