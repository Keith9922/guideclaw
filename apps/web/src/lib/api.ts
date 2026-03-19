export type ApiProject = {
  id: string;
  title: string;
  summary?: string | null;
  stage: string;
  created_at: string;
  updated_at: string;
};

export type ApiEvidence = {
  source: string;
  source_id?: string | null;
  chunk_id?: string | null;
  source_type?: ApiKnowledgeSource["source_type"] | null;
  page?: number | null;
  page_to?: number | null;
  snippet: string;
  citation?: string | null;
  doi?: string | null;
  url?: string | null;
};

export type ApiLiteratureCard = {
  id: string;
  project_id: string;
  title: string;
  research_question: string;
  method: string;
  data_source: string;
  key_result: string;
  limitations: string[];
  evidence: ApiEvidence[];
};

export type ApiGapCard = {
  id: string;
  project_id: string;
  title: string;
  gap_type: string;
  why_it_matters: string;
  novelty_score: number;
  importance_score: number;
  feasibility_score: number;
  evidence: ApiEvidence[];
};

export type ApiPlanCard = {
  id: string;
  project_id: string;
  research_question: string;
  boundary: string;
  data_source: string;
  metrics: string[];
  methods: string[];
  validation: string;
  evidence: ApiEvidence[];
};

export type ApiMeetingNote = {
  id: string;
  project_id: string;
  decisions: string[];
  open_questions: string[];
  todos: string[];
  next_step: string;
  evidence: ApiEvidence[];
};

export type ApiArtifactBundle = {
  literature_cards: ApiLiteratureCard[];
  gap_cards: ApiGapCard[];
  plan_cards: ApiPlanCard[];
  meeting_notes: ApiMeetingNote[];
};

export type WorkflowStep = {
  role: AgentRole;
  title: string;
  summary: string;
};

export type ProjectResearchState = {
  project_id: string;
  research_focus: string;
  why_now: string;
  key_questions: string[];
  search_queries: string[];
  recommended_gap_title?: string | null;
  current_hypothesis?: string | null;
  next_step?: string | null;
  literature_provider?: string | null;
  provider_note?: string | null;
  last_investigated_at?: string | null;
};

export type AgentTask = {
  id: string;
  project_id: string;
  role: AgentRole;
  title: string;
  objective: string;
  status: "pending" | "running" | "completed" | "blocked";
  inputs: string[];
  expected_output: string;
  output_summary?: string | null;
  depends_on: string[];
  evidence_source_ids: string[];
  artifact_ids: string[];
  created_at: string;
  updated_at: string;
};

export type ApiKnowledgeSource = {
  id: string;
  project_id: string;
  source_type: "openalex" | "bohrium_paper_search" | "pdf_upload" | "manual" | "skill_ingest";
  external_id?: string | null;
  title: string;
  year?: string | null;
  venue?: string | null;
  doi?: string | null;
  url?: string | null;
  abstract?: string | null;
  citation?: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeHit = {
  source_id: string;
  chunk_id?: string | null;
  source_type: ApiKnowledgeSource["source_type"];
  title: string;
  excerpt: string;
  score: number;
  citation?: string | null;
  doi?: string | null;
  url?: string | null;
};

export type GeneratedDocument = {
  id: string;
  project_id: string;
  doc_type: "project_summary" | "agent_run" | "follow_up" | "result_summary";
  title: string;
  role?: AgentRole | null;
  content: string;
  source: "minimax" | "openclaw" | "system";
  model?: string | null;
  session_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type ResultSummaryReference = {
  title: string;
  reason: string;
  citation?: string | null;
  doi?: string | null;
  url?: string | null;
  source_type?: ApiKnowledgeSource["source_type"] | null;
};

export type ResultSummarySection = {
  title: string;
  content: string;
  bullets: string[];
};

export type ResultSummaryAction = {
  title: string;
  description: string;
};

export type ResultSummary = {
  project_id: string;
  project_title: string;
  stage_label: string;
  intro: string;
  sections: ResultSummarySection[];
  recommended_reading: ResultSummaryReference[];
  next_actions: ResultSummaryAction[];
  knowledge_highlights: ResultSummaryReference[];
  generated_at: string;
  pdf_url: string;
};

export type PdfUploadResult = {
  source: ApiKnowledgeSource;
  chunk_count: number;
};

export type ProjectCreateInput = {
  title: string;
  summary?: string;
  stage?: "literature_review" | "gap_analysis" | "proposal" | "meeting_notes";
};

export type AgentRole =
  | "principal_investigator"
  | "literature_assistant"
  | "gap_analyst"
  | "study_designer"
  | "meeting_secretary";

export type WorkbenchData = {
  project: ApiProject;
  research_state: ProjectResearchState;
  artifacts: ApiArtifactBundle;
  workflow_steps: WorkflowStep[];
  agent_tasks: AgentTask[];
  knowledge_sources: ApiKnowledgeSource[];
  generated_documents: GeneratedDocument[];
  source: "api" | "mock";
};

export type LlmSummary = {
  project_id: string;
  model: string;
  source: "minimax";
  content: string;
};

export type AgentRunResult = {
  project_id: string;
  role: AgentRole;
  skill: string;
  model: string | null;
  session_id: string | null;
  duration_ms: number | null;
  content: string;
};

export type InvestigationResult = {
  project: ApiProject;
  research_state: ProjectResearchState;
  artifacts: ApiArtifactBundle;
  workflow_steps: WorkflowStep[];
  agent_tasks: AgentTask[];
};

export type TranslateResult = {
  project_id: string;
  source_text: string;
  translated_text: string;
  model?: string | null;
};

export type FollowUpDelegate = {
  role: Exclude<AgentRole, "principal_investigator">;
  objective: string;
};

export type FollowUpDelegateResult = {
  role: Exclude<AgentRole, "principal_investigator">;
  title: string;
  objective: string;
  status: "completed" | "failed";
  content: string;
  model?: string | null;
  skill?: string | null;
  duration_ms?: number | null;
};

export type FollowUpResult = {
  project_id: string;
  question: string;
  pi_focus: string;
  delegates: FollowUpDelegate[];
  delegate_results: FollowUpDelegateResult[];
  content: string;
  model?: string | null;
};

export type RuntimeHealth = {
  status: string;
  environment: string;
  project_bootstrap_mode: string;
  minimax: {
    base_url: string;
    api_key_configured: boolean;
    model_configured: boolean;
    ready: boolean;
  };
  openclaw: {
    integration_mode: string;
    binary: string;
    profile: string;
    agent: string;
    channel_server: boolean;
    call_path: string;
    workspace_skills_require_api_env?: boolean;
  };
  bohrium?: {
    base_url: string;
    access_key_configured: boolean;
    ready: boolean;
    installed_workspace_skills?: string[];
  };
};

const API_BASE_URL =
  process.env.GUIDECLAW_API_BASE_URL ??
  process.env.NEXT_PUBLIC_GUIDECLAW_API_BASE_URL ??
  "http://127.0.0.1:8000";

export class ApiRequestError extends Error {
  status?: number;
  path: string;

  constructor(path: string, message: string, status?: number) {
    super(message);
    this.name = "ApiRequestError";
    this.path = path;
    this.status = status;
  }
}

async function buildRequestError(path: string, response: Response): Promise<ApiRequestError> {
  let detail = "";
  try {
    const payload = (await response.json()) as { detail?: string };
    detail = payload.detail ?? "";
  } catch {
    try {
      detail = await response.text();
    } catch {
      detail = "";
    }
  }

  const message = detail
    ? `请求 ${path} 失败（${response.status}）：${detail}`
    : `请求 ${path} 失败（${response.status}）`;
  return new ApiRequestError(path, message, response.status);
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const hasBody = typeof init?.body !== "undefined";
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: {
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw await buildRequestError(path, response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function requestFormData<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    cache: "no-store",
    body,
  });

  if (!response.ok) {
    throw await buildRequestError(path, response);
  }

  return (await response.json()) as T;
}

export async function getWorkbenchData(projectId?: string): Promise<WorkbenchData | null> {
  if (!projectId) {
    return null;
  }

  try {
    const workspace = await requestJson<
      Omit<WorkbenchData, "source">
    >(`/projects/${projectId}/workspace`);

    return {
      ...workspace,
      source: "api",
    };
  } catch {
    return null;
  }
}

export async function getWorkbenchDataStrict(projectId?: string): Promise<WorkbenchData | null> {
  if (!projectId) {
    return null;
  }

  const workspace = await requestJson<
    Omit<WorkbenchData, "source">
  >(`/projects/${projectId}/workspace`);

  return {
    ...workspace,
    source: "api",
  };
}

export async function getProjects(): Promise<ApiProject[]> {
  try {
    return await requestJson<ApiProject[]>("/projects");
  } catch {
    return [];
  }
}

export async function getProjectsStrict(): Promise<ApiProject[]> {
  return requestJson<ApiProject[]>("/projects");
}

export async function createProject(payload: ProjectCreateInput): Promise<ApiProject> {
  return requestJson<ApiProject>("/projects", {
    method: "POST",
    body: JSON.stringify({
      stage: "literature_review",
      ...payload,
    }),
  });
}

export async function deleteProject(projectId: string): Promise<void> {
  await requestJson<void>(`/projects/${projectId}`, {
    method: "DELETE",
  });
}

export async function investigateProject(projectId: string): Promise<InvestigationResult> {
  return requestJson<InvestigationResult>(`/projects/${projectId}/investigate`, {
    method: "POST",
  });
}

export async function getKnowledgeSearch(projectId: string, query: string): Promise<KnowledgeHit[]> {
  return requestJson<KnowledgeHit[]>(
    `/projects/${projectId}/knowledge-search?q=${encodeURIComponent(query)}`,
  );
}

export async function uploadProjectPdf(projectId: string, file: File): Promise<PdfUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  return requestFormData<PdfUploadResult>(`/projects/${projectId}/pdf-upload`, formData);
}

export async function getLlmSummary(projectId?: string): Promise<LlmSummary | null> {
  if (!projectId) {
    return null;
  }

  try {
    return await requestJson<LlmSummary>(`/projects/${projectId}/llm-summary`, {
      method: "POST",
    });
  } catch {
    return null;
  }
}

export async function runOpenClawRole(
  role: AgentRole,
  projectId: string,
): Promise<AgentRunResult> {
  return requestJson<AgentRunResult>(`/projects/${projectId}/agent-run`, {
    method: "POST",
    body: JSON.stringify({ role }),
  });
}

export async function translateProjectText(
  projectId: string,
  text: string,
): Promise<TranslateResult> {
  return requestJson<TranslateResult>(`/projects/${projectId}/translate`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function followUpProject(
  projectId: string,
  question: string,
): Promise<FollowUpResult> {
  return requestJson<FollowUpResult>(`/projects/${projectId}/follow-up`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export async function getRuntimeHealth(): Promise<RuntimeHealth | null> {
  try {
    return await requestJson<RuntimeHealth>("/health");
  } catch {
    return null;
  }
}

export async function getRuntimeHealthStrict(): Promise<RuntimeHealth> {
  return requestJson<RuntimeHealth>("/health");
}

export async function getResultSummary(projectId?: string): Promise<ResultSummary | null> {
  if (!projectId) {
    return null;
  }
  try {
    return await requestJson<ResultSummary>(`/projects/${projectId}/result-summary`);
  } catch {
    return null;
  }
}

export async function getResultSummaryStrict(projectId?: string): Promise<ResultSummary | null> {
  if (!projectId) {
    return null;
  }
  return requestJson<ResultSummary>(`/projects/${projectId}/result-summary`);
}
