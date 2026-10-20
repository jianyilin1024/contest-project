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
/* ==================== 单文档 AI 分析 ==================== */

export type AnalysisSegment = {
  id: number;
  section: string;
  text: string;
  chars: number;
  features: Record<string, number>;
};

export type AuthorshipGroup = {
  id: string;
  label: string;
  features: string[];
  units: number;
  characters: number;
  avg_sentence: number;
  unit_ids: number[];
};

export type AuthorshipAssignment = {
  unit_id: number;
  group_id: string;
  confidence: number;
  reason: string;
  section: string;
  preview: string;
};

export type AuthorshipResult = {
  heterogeneity: string;
  conclusion: string;
  groups: AuthorshipGroup[];
  assignments: AuthorshipAssignment[];
};

export type StyleIssue = {
  type: string;
  title: string;
  detail: string;
  examples: string[];
  suggestion: string;
};

export type StyleAdvice = {
  canonical_style: string;
  issues: StyleIssue[];
  plan: string[];
};

export type LayoutConvention = {
  aspect: string;
  observation: string;
  consistent: boolean;
  suggestion: string;
};

export type LayoutResult = {
  summary: string;
  conventions: LayoutConvention[];
  facts: Record<string, unknown>;
};

export type SingleAnalysisResponse = {
  title: string;
  filename: string;
  stats: {
    sections: number;
    paragraphs: number;
    characters: number;
    units_total: number;
    units_analyzed: number;
  };
  authorship: AuthorshipResult;
  style: StyleAdvice;
  layout: LayoutResult;
  segments: AnalysisSegment[];
  model: string;
  elapsed_ms: number;
};

export type UnifyResponse = {
  markdown: string;
  rewritten: number;
  failed: number;
  notes: string[];
};

export async function analyzeSingle(
  file: File,
  title: string,
  signal?: AbortSignal,
): Promise<SingleAnalysisResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);

  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/single`, {
    method: "POST",
    body: form,
    signal,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as SingleAnalysisResponse;
}

export async function unifyDocument(
  segments: { id: number; section: string; text: string; group_id: string }[],
  styleBrief: string,
  title: string,
  targetGroup: string | null,
): Promise<UnifyResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/unify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title,
      style_brief: styleBrief,
      segments,
      target_group: targetGroup,
    }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as UnifyResponse;
}
/* ==================== F5 排版 ==================== */

export type TemplateInfo = {
  key: string;
  name: string;
  description: string;
  toc: boolean;
  numbering: boolean;
  page_numbers: boolean;
};

export type ReferenceEntry = {
  index: number;
  original: string;
  formatted: string;
  type: string;
  note: string;
};

export type ReferenceResponse = {
  found: boolean;
  heading: string;
  entries: ReferenceEntry[];
  markdown: string;
  notes: string[];
};

export async function fetchTemplates(signal?: AbortSignal): Promise<TemplateInfo[]> {
  return getJson<TemplateInfo[]>("/api/v1/format/templates", signal);
}

export async function renderDocx(payload: {
  markdown: string;
  title: string;
  template: string;
  toc: boolean;
  numbering: boolean;
  page_numbers: boolean;
}): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/v1/format/docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return await response.blob();
}

export async function formatReferences(markdown: string): Promise<ReferenceResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/format/references`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as ReferenceResponse;
}
