/** 后端接口地址与统一请求封装。 */

/**
 * 后端地址。
 * - 生产：留空，走同源（Nginx 把 /api/ 反代到后端），镜像因此与域名解耦；
 * - 本地：在 apps/web/.env.local 里写 http://localhost:8000。
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

/** 供界面展示用的人类可读地址。 */
export const API_BASE_LABEL = API_BASE_URL || "同源 /api";

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
/* ==================== F3 过渡段落 ==================== */

export type TransitionBlock = {
  id: number;
  kind: string;
  level: number;
  text: string;
};

export type DeAIInfo = {
  before_score: number;
  after_score: number;
  issues: string[];
  applied: boolean;
  original: string | null;
  remaining: string[];
  rejected: string[];
};

export type TransitionOption = {
  id: string;
  label: string;
  text: string;
  overlap: number;
  duplicate: boolean;
  deai?: DeAIInfo | null;
};

export type TransitionBoundary = {
  id: string;
  after_block_id: number;
  before_block_id: number;
  section_from: string;
  section_to: string;
  context_before: string;
  context_after: string;
  needs: boolean;
  reason: string;
  confidence: number;
  options: TransitionOption[];
};

export type TransitionResponse = {
  title: string;
  blocks: TransitionBlock[];
  boundaries: TransitionBoundary[];
  stats: { candidates: number; needed: number; skipped: number };
  elapsed_ms: number;
};

export type ApplyResult = {
  markdown: string;
  inserted: number;
};

export async function analyzeTransitions(
  markdown: string,
  title: string,
  deai = true,
  signal?: AbortSignal,
): Promise<TransitionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/transition/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown, title, deai }),
    signal,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as TransitionResponse;
}

export async function applyTransitions(
  blocks: TransitionBlock[],
  insertions: { after_block_id: number; text: string }[],
): Promise<ApplyResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/transition/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blocks, insertions }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as ApplyResult;
}
/* ==================== F7 参考文献 ==================== */

export type ReferenceRecord = {
  title: string;
  authors: string[];
  year: number | null;
  venue: string;
  volume: string;
  issue: string;
  pages: string;
  doi: string;
  url: string;
  kind: string;
  source: string;
  cited_by: number;
  relevance: number;
  abstract: string;
};

export type CitationEntry = {
  index: number;
  text: string;
  /** 同一文献的 BibTeX 形式 */
  bibtex: string;
  record: ReferenceRecord;
};

export type ReferenceSearchResponse = {
  query: string;
  total: number;
  entries: CitationEntry[];
  /** 全部条目的 BibTeX，便于一次性复制 */
  bibtex: string;
};

export async function searchReferences(
  query: string,
  limit = 8,
  sources: string[] = ["academic", "book", "web"],
): Promise<ReferenceSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/references/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit, sources }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as ReferenceSearchResponse;
}

export async function insertReferences(
  markdown: string,
  entries: string[],
): Promise<{ markdown: string; inserted: number }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/references/insert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown, entries }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as { markdown: string; inserted: number };
}

/* ==================== 一键成稿 ==================== */

export type PipelineStep = {
  name: string;
  status: "ok" | "skipped" | "failed";
  detail: string;
  elapsed_ms: number;
};

export type OneClickResponse = {
  title: string;
  merged_markdown: string;
  final_markdown: string;
  stats: Record<string, unknown>;
  duplicates: unknown[];
  terms: unknown[];
  warnings: string[];
  plan: AgentPlan;
  checks: CheckItem[];
  transitions: { candidates: number; needed: number; applied: number; skipped: boolean };
  references: {
    query: string;
    queries?: string[];
    entries: CitationEntry[];
    inserted: number;
    skipped: boolean;
  };
  steps: PipelineStep[];
  elapsed_ms: number;
};

export async function runOneClick(
  files: File[],
  meta: { author: string; title: string }[],
  title: string,
  options: { deai: boolean; addTransitions: boolean; findReferences: boolean; referenceLimit: number },
): Promise<OneClickResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  form.append("meta", JSON.stringify(meta));
  form.append("title", title);
  form.append("deai", String(options.deai));
  form.append("add_transitions", String(options.addTransitions));
  form.append("find_references", String(options.findReferences));
  form.append("reference_limit", String(options.referenceLimit));

  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/oneclick`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as OneClickResponse;
}
/* ==================== F6 数据助手 ==================== */

export type DataGap = { description: string; query: string };

export type DataSuggestion = {
  value: string;
  context: string;
  source_title: string;
  source_url: string;
  quote: string;
  confidence: number;
  gap: string;
};

export type DataAssistResponse = {
  gaps: DataGap[];
  suggestions: DataSuggestion[];
  searched: number;
};

export async function assistData(text: string): Promise<DataAssistResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/data/assist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as DataAssistResponse;
}
/* ==================== F2 分工记录 ==================== */

export type Member = { id: number; name: string; role: string };
export type Task = {
  id: number;
  title: string;
  section: string;
  status: "todo" | "doing" | "done";
  due_date: string | null;
  note: string;
  member_id: number | null;
  member_name: string;
};
export type Project = {
  id: number;
  name: string;
  description: string;
  members: Member[];
  tasks: Task[];
  stats: Record<string, number>;
};
export type ProjectBrief = {
  id: number;
  name: string;
  description: string;
  member_count: number;
  task_count: number;
  done_count: number;
};

async function send<T>(path: string, method: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as T;
}

export const listProjects = () => getJson<ProjectBrief[]>("/api/v1/projects");
export const createProject = (name: string, description = "") =>
  send<Project>("/api/v1/projects", "POST", { name, description });
export const getProject = (id: number) => getJson<Project>(`/api/v1/projects/${id}`);
export const deleteProject = (id: number) =>
  send<{ deleted: number }>(`/api/v1/projects/${id}`, "DELETE");
export const addMember = (projectId: number, name: string, role = "成员") =>
  send<Member>(`/api/v1/projects/${projectId}/members`, "POST", { name, role });
export const removeMember = (id: number) =>
  send<{ deleted: number }>(`/api/v1/members/${id}`, "DELETE");
export const createTask = (
  projectId: number,
  payload: { title: string; section?: string; member_id?: number | null; due_date?: string | null },
) => send<Task>(`/api/v1/projects/${projectId}/tasks`, "POST", payload);
export const updateTask = (id: number, patch: Partial<Task>) =>
  send<Task>(`/api/v1/tasks/${id}`, "PATCH", patch);
export const deleteTask = (id: number) =>
  send<{ deleted: number }>(`/api/v1/tasks/${id}`, "DELETE");
/* ==================== F4 逐段风格统一 ==================== */

export type RewriteSegment = {
  id: number;
  original: string;
  rewritten: string;
  changed: boolean;
  reason: string;
};

export async function rewriteStyle(markdown: string): Promise<{
  segments: RewriteSegment[];
  changed_count: number;
}> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/rewrite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as { segments: RewriteSegment[]; changed_count: number };
}

export async function assembleRewrite(
  markdown: string,
  segments: RewriteSegment[],
  accepted: number[],
): Promise<{ markdown: string; applied: number }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/rewrite/assemble`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown, segments, accepted }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as { markdown: string; applied: number };
}
/* ==================== 一键成稿（SSE 流式） ==================== */

export type AgentPlan = {
  need_transitions: boolean;
  need_references: boolean;
  reference_limit: number;
  transition_hint?: string;
  reasoning: string;
  source?: "model" | "user" | "fallback";
};

export type CheckItem = { name: string; ok: boolean; detail: string };

export type PipelineEvent =
  | { type: "plan"; steps: string[] }
  | { type: "step"; step: PipelineStep }
  | { type: "agent"; plan: AgentPlan }
  | { type: "verify"; checks: CheckItem[] }
  | { type: "result"; data: OneClickResponse }
  | { type: "error"; detail: string };

/**
 * 与服务端 /oneclick/stream 对接，边执行边回调事件。
 *
 * 不用 EventSource：接口需要 POST + multipart，只能自己解析 SSE 帧。
 */
export async function runOneClickStream(
  files: File[],
  meta: { author: string; title: string }[],
  title: string,
  options: { deai: boolean; addTransitions: boolean; findReferences: boolean; referenceLimit: number },
  onEvent: (event: PipelineEvent) => void,
): Promise<OneClickResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  form.append("meta", JSON.stringify(meta));
  form.append("title", title);
  form.append("deai", String(options.deai));
  form.append("add_transitions", String(options.addTransitions));
  form.append("find_references", String(options.findReferences));
  form.append("reference_limit", String(options.referenceLimit));

  const response = await fetch(`${API_BASE_URL}/api/v1/pipeline/oneclick/stream`, {
    method: "POST",
    body: form,
  });
  if (!response.ok || !response.body) {
    throw new Error(await readError(response));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: OneClickResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");

      let eventName = "message";
      const dataLines: string[] = [];
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }
      if (dataLines.length === 0) continue;
      let payload: unknown;
      try {
        payload = JSON.parse(dataLines.join("\n"));
      } catch {
        continue;
      }
      if (eventName === "result") {
        result = payload as OneClickResponse;
        onEvent({ type: "result", data: result });
      } else if (eventName === "step") {
        onEvent({ type: "step", step: payload as PipelineStep });
      } else if (eventName === "plan") {
        onEvent({ type: "plan", steps: (payload as { steps: string[] }).steps });
      } else if (eventName === "agent") {
        onEvent({ type: "agent", plan: payload as AgentPlan });
      } else if (eventName === "verify") {
        onEvent({ type: "verify", checks: (payload as { checks: CheckItem[] }).checks });
      } else if (eventName === "error") {
        const detail = (payload as { detail?: string }).detail ?? "生成失败";
        onEvent({ type: "error", detail });
        throw new Error(detail);
      }
    }
  }

  if (!result) {
    throw new Error("连接中断，未收到完整结果");
  }
  return result;
}
/* ==================== 引用建议 ==================== */

export type CitationCandidate = {
  index: number;
  text: string;
  bibtex: string;
  title: string;
  year: number | null;
  venue: string;
  doi: string;
};

export type CitationSpot = {
  sentence: string;
  reason: string;
  query: string;
  candidates: CitationCandidate[];
};

export type CitationSuggestResponse = {
  spots: CitationSpot[];
  total: number;
  scanned_paragraphs: number;
};

/** 上传一篇论文，让 AI 指出哪些句子该补引用，并为每处给出候选文献。 */
export async function suggestCitations(file: File): Promise<CitationSuggestResponse> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/v1/citations/suggest`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return (await response.json()) as CitationSuggestResponse;
}
