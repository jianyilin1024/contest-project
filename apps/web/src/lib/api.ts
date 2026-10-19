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

/* ==================== F1 多部分整合 ==================== */

export type MergeDocumentStat = {
  filename: string;
  author: string;
  headings: number;
  characters: number;
};

export type MergeStats = {
  documents: number;
  sections: number;
  sub_sections: number;
  characters: number;
  duplicates: number;
  cross_duplicates: number;
  term_conflicts: number;
  per_document: MergeDocumentStat[];
};

export type MergeOutlineNode = {
  level: number;
  number: string;
  title: string;
  source: string;
  characters: number;
  preview: string;
};

export type MergeOccurrence = {
  source: string;
  author: string;
  section: string;
};

export type MergeDuplicate = {
  text: string;
  length: number;
  occurrences: MergeOccurrence[];
  cross_document: boolean;
};

export type MergeTerm = {
  short: string;
  long: string;
  short_docs: string[];
  long_docs: string[];
  total: number;
};

export type MergeResponse = {
  title: string;
  stats: MergeStats;
  outline: MergeOutlineNode[];
  duplicates: MergeDuplicate[];
  terms: MergeTerm[];
  warnings: string[];
  markdown: string;
};

export type MergeMeta = { author: string; title: string };

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (body.detail) return JSON.stringify(body.detail);
  } catch {
    /* 忽略解析失败，返回状态码 */
  }
  return `HTTP ${response.status}`;
}

export async function analyzeMerge(
  files: File[],
  meta: MergeMeta[],
  title: string,
  signal?: AbortSignal,
): Promise<MergeResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  form.append("meta", JSON.stringify(meta));
  form.append("title", title);

  const response = await fetch(`${API_BASE_URL}/api/v1/merge/analyze`, {
    method: "POST",
    body: form,
    signal,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as MergeResponse;
}

export async function exportMerge(
  markdown: string,
  title: string,
  format: "md" | "docx",
): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/v1/merge/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown, title, format }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return await response.blob();
}
