import type { LucideIcon } from "lucide-react";
import type {
  AgentTask,
  AgentRole,
  ApiKnowledgeSource,
  GeneratedDocument,
  LlmSummary,
  ProjectResearchState,
  ResultSummary,
  RuntimeHealth,
  WorkbenchData,
  WorkflowStep,
} from "@/lib/api";

export type InsightCategory = "all" | "literature" | "gap" | "plan" | "meeting";

export type DetailItem = {
  label: string;
  value: string | string[];
};

export type EvidenceItem = {
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

export type InsightCard = {
  id: string;
  category: Exclude<InsightCategory, "all">;
  title: string;
  summary: string;
  status: string;
  tags: string[];
  details: DetailItem[];
  evidence: EvidenceItem[];
};

export type RoleCard = {
  id: AgentRole;
  skill: string;
  name: string;
  title: string;
  description: string;
  stage: string;
  state: "已完成" | "执行中" | "待命";
  progress: number;
  outputSummary?: string;
  workflowIndex?: number;
  source: "workflow" | "stage";
};

export type DashboardView = "workspace" | "artifacts" | "roles" | "projects" | "knowledge" | "results";

export type StreamMeta = {
  skill?: string;
  model?: string | null;
  session_id?: string | null;
  duration_ms?: number | null;
};

export type ViewMeta = {
  label: string;
  title: string;
  description: string;
  icon: LucideIcon;
};

export type EmptyViewMeta = {
  title: string;
  description: string;
  actionLabel: string;
};

export type ProjectViewModel = {
  id: string;
  title: string;
  stage: string;
  summary: string;
  lastSync: string;
};

export type ProjectPulse = {
  focus: string;
  whyNow: string;
  nextStep: string;
  provider: string;
  recommendedGap: string;
};

export type KnowledgeCard = ApiKnowledgeSource & {
  label: string;
};

export type AgentBoardTask = AgentTask & {
  roleName: string;
  isPrimary: boolean;
};

export type DashboardShellProps = {
  activeView: DashboardView;
  projects: Array<{
    id: string;
    title: string;
    summary?: string | null;
    stage: string;
    created_at: string;
    updated_at: string;
  }>;
  workbench: WorkbenchData | null;
  resultSummary: ResultSummary | null;
  llmSummary: LlmSummary | null;
  runtimeHealth: RuntimeHealth | null;
  pageErrors?: string[];
  hasBlockingError?: boolean;
};

export type StoredDocument = GeneratedDocument;

export type DocumentPreview = GeneratedDocument;

export type WorkflowTimelineItem = WorkflowStep & {
  index: number;
  roleName: string;
  handoffLabel?: string;
};

export type ResearchStateLike = ProjectResearchState | null | undefined;
