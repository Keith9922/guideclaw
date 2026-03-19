"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { FormEvent } from "react";
import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import {
  createProject,
  deleteProject,
  followUpProject,
  getKnowledgeSearch,
  getLlmSummary,
  investigateProject,
  uploadProjectPdf,
  type ApiProject,
  type FollowUpResult,
  type KnowledgeHit,
  type LlmSummary,
  type RuntimeHealth,
  type WorkbenchData,
} from "@/lib/api";
import {
  buildInsightCards,
  buildKnowledgeCards,
  buildProjectPulse,
  buildRoleCards,
  emptyViewCopy,
  getStageLabel,
  stageMeta,
  viewLabels,
} from "@/components/dashboard/content";
import { CreateProjectDialog, RoleRunDialog } from "@/components/dashboard/dialogs";
import { DashboardPageNav } from "@/components/dashboard/page-nav";
import { DetailSidebar } from "@/components/dashboard/detail-sidebar";
import { ProjectSidebar } from "@/components/dashboard/project-sidebar";
import { DashboardTopbar } from "@/components/dashboard/topbar";
import { WorkspaceMainPanel } from "@/components/dashboard/view-panels";
import type {
  DashboardShellProps,
  DashboardView,
  ProjectViewModel,
  RoleCard,
  StoredDocument,
  StreamMeta,
} from "@/components/dashboard/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_GUIDECLAW_API_BASE_URL ??
  process.env.GUIDECLAW_API_BASE_URL ??
  "http://127.0.0.1:8000";

function toProjectViewModel(workbench: WorkbenchData | null): ProjectViewModel | null {
  if (!workbench) {
    return null;
  }

  return {
    id: workbench.project.id,
    title: workbench.project.title,
    stage: workbench.project.stage,
    summary: workbench.project.summary ?? "这个项目还没有填写研究说明。",
    lastSync: new Date(workbench.project.updated_at).toLocaleString("zh-CN"),
  };
}

function getHeaderCopy(
  activeView: DashboardView,
  project: ProjectViewModel | null,
  projectCount: number,
  knowledgeCount: number,
) {
  const activeViewMeta = viewLabels[activeView];
  const stage = project
    ? stageMeta[project.stage] ?? {
        label: getStageLabel(project.stage),
        description: "当前阶段信息尚未映射。",
      }
    : {
        label: "未开始",
        description: "先创建一个真实课题，再进入工作区推进研究。",
      };

  return {
    title:
      activeView === "projects"
        ? "引路虾项目管理"
        : activeViewMeta.title,
    description:
      activeView === "projects"
        ? "一个课题对应一个独立工作流。先在这里创建和切换项目，再进入工作区推进研究。"
        : project
          ? `当前项目：${project.title}。${stage.description}`
          : activeViewMeta.description,
    badges: [`${projectCount} 个课题`, `${knowledgeCount} 条知识源`, stage.label],
    currentStage: stage,
  };
}

export function DashboardShell({
  activeView,
  projects,
  workbench,
  resultSummary,
  llmSummary,
  runtimeHealth,
  pageErrors = [],
  hasBlockingError = false,
}: DashboardShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isRouting, startTransition] = useTransition();

  const project = useMemo(() => toProjectViewModel(workbench), [workbench]);
  const cards = useMemo(() => buildInsightCards(workbench), [workbench]);
  const knowledgeCards = useMemo(
    () => buildKnowledgeCards(workbench?.knowledge_sources ?? []),
    [workbench?.knowledge_sources],
  );
  const pulse = useMemo(() => buildProjectPulse(workbench), [workbench]);
  const roles = useMemo(
    () => buildRoleCards(workbench?.research_state, workbench?.workflow_steps ?? [], workbench?.agent_tasks ?? []),
    [workbench?.research_state, workbench?.workflow_steps, workbench?.agent_tasks],
  );
  const generatedDocuments = useMemo<StoredDocument[]>(
    () => workbench?.generated_documents ?? [],
    [workbench?.generated_documents],
  );
  const latestSummaryDocument = useMemo(
    () => generatedDocuments.find((item) => item.doc_type === "project_summary") ?? null,
    [generatedDocuments],
  );

  const [selectedCardId, setSelectedCardId] = useState<string>(cards[0]?.id ?? "");
  const [summaryState, setSummaryState] = useState<LlmSummary | null>(
    llmSummary ??
      (latestSummaryDocument
        ? {
            project_id: latestSummaryDocument.project_id,
            model: latestSummaryDocument.model ?? "stored-summary",
            source: "minimax",
            content: latestSummaryDocument.content,
          }
        : null),
  );
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [investigationLoading, setInvestigationLoading] = useState(false);
  const [projectDialogOpen, setProjectDialogOpen] = useState(false);
  const [projectTitleInput, setProjectTitleInput] = useState("");
  const [projectSummaryInput, setProjectSummaryInput] = useState("");
  const [projectCreateLoading, setProjectCreateLoading] = useState(false);
  const [projectCreateError, setProjectCreateError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [streamLoading, setStreamLoading] = useState(false);
  const [streamStatus, setStreamStatus] = useState("等待执行");
  const [streamError, setStreamError] = useState<string | null>(null);
  const [streamContent, setStreamContent] = useState("");
  const [streamMeta, setStreamMeta] = useState<StreamMeta | null>(null);
  const [activeRole, setActiveRole] = useState<RoleCard | null>(null);
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [knowledgeHits, setKnowledgeHits] = useState<KnowledgeHit[]>([]);
  const [pdfUploadLoading, setPdfUploadLoading] = useState(false);
  const [pdfUploadError, setPdfUploadError] = useState<string | null>(null);
  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [followUpError, setFollowUpError] = useState<string | null>(null);
  const [followUpResult, setFollowUpResult] = useState<FollowUpResult | null>(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(activeView !== "workspace");
  const sourceRef = useRef<EventSource | null>(null);

  const selectedCard = cards.find((card) => card.id === selectedCardId) ?? cards[0] ?? null;
  const activeViewMeta = viewLabels[activeView];
  const emptyStateMeta = emptyViewCopy[activeView];
  const headerCopy = getHeaderCopy(activeView, project, projects.length, knowledgeCards.length);

  useEffect(() => {
    setSelectedCardId((current) => {
      if (current && cards.some((card) => card.id === current)) {
        return current;
      }
      return cards[0]?.id ?? "";
    });
  }, [cards]);

  useEffect(() => {
    setSummaryState(
      llmSummary ??
        (latestSummaryDocument
          ? {
              project_id: latestSummaryDocument.project_id,
              model: latestSummaryDocument.model ?? "stored-summary",
              source: "minimax",
              content: latestSummaryDocument.content,
            }
          : null),
    );
  }, [llmSummary, latestSummaryDocument, workbench?.project.id]);

  useEffect(() => {
    setKnowledgeHits([]);
    setKnowledgeQuery("");
    setPdfUploadError(null);
    setFollowUpQuestion("");
    setFollowUpError(null);
    setFollowUpResult(null);
  }, [workbench?.project.id]);

  useEffect(() => {
    if (activeView === "projects") {
      setDetailPanelOpen(false);
      return;
    }
    if (activeView === "results") {
      setDetailPanelOpen(false);
      return;
    }
    if (activeView !== "workspace") {
      setDetailPanelOpen(true);
    }
  }, [activeView]);

  function closeStream() {
    sourceRef.current?.close();
    sourceRef.current = null;
  }

  function navigateToProject(projectId: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("projectId", projectId);
    startTransition(() => {
      router.push(`${pathname}?${params.toString()}`);
    });
  }

  function navigateToView(view: DashboardView) {
    const params = new URLSearchParams(searchParams.toString());
    if (project?.id) {
      params.set("projectId", project.id);
    } else {
      params.delete("projectId");
    }
    const pathMap: Record<DashboardView, string> = {
      workspace: "/workspace",
      artifacts: "/artifacts",
      knowledge: "/knowledge",
      results: "/results",
      roles: "/roles",
      projects: "/projects",
    };
    startTransition(() => {
      const query = params.toString();
      router.push(query ? `${pathMap[view]}?${query}` : pathMap[view]);
    });
  }

  async function handleRefreshSummary() {
    if (!workbench) return;
    try {
      setSummaryLoading(true);
      const nextSummary = await getLlmSummary(workbench.project.id);
      setSummaryState(nextSummary);
      router.refresh();
    } finally {
      setSummaryLoading(false);
    }
  }

  async function handleSearchKnowledge() {
    if (!workbench) return;
    const nextHits = await getKnowledgeSearch(workbench.project.id, knowledgeQuery.trim());
    setKnowledgeHits(nextHits);
  }

  async function handleUploadPdf(file: File) {
    if (!workbench) return;
    try {
      setPdfUploadLoading(true);
      setPdfUploadError(null);
      await uploadProjectPdf(workbench.project.id, file);
      router.refresh();
    } catch {
      setPdfUploadError("PDF 上传或解析失败，请稍后重试。");
    } finally {
      setPdfUploadLoading(false);
    }
  }

  async function handleSubmitFollowUp() {
    if (!workbench || !followUpQuestion.trim()) return;
    try {
      setFollowUpLoading(true);
      setFollowUpError(null);
      const result = await followUpProject(workbench.project.id, followUpQuestion.trim());
      setFollowUpResult(result);
      setFollowUpQuestion("");
      router.refresh();
    } catch (error) {
      setFollowUpError(error instanceof Error ? error.message : "追问执行失败，请稍后重试。");
    } finally {
      setFollowUpLoading(false);
    }
  }

  function handleRunRole(role: RoleCard) {
    if (!workbench) return;
    closeStream();
    setActiveRole(role);
    setStreamLoading(true);
    setStreamStatus("OpenClaw 正在准备角色上下文");
    setStreamError(null);
    setStreamContent("");
    setStreamMeta(null);
    setModalOpen(true);

    const source = new EventSource(
      `${API_BASE_URL}/projects/${encodeURIComponent(workbench.project.id)}/agent-run/stream?role=${encodeURIComponent(role.id)}`,
    );
    sourceRef.current = source;

    source.onmessage = (event) => {
      const payload = JSON.parse(event.data) as
        | { type: "status"; message: string }
        | { type: "meta"; skill?: string; model?: string | null; session_id?: string | null; duration_ms?: number | null }
        | { type: "delta"; content: string }
        | { type: "error"; message: string }
        | { type: "done" };

      if (payload.type === "status") {
        setStreamStatus(payload.message);
        return;
      }
      if (payload.type === "meta") {
        setStreamMeta(payload);
        setStreamStatus("角色已接管，正在回传内容");
        return;
      }
      if (payload.type === "delta") {
        setStreamContent((current) => current + payload.content);
        return;
      }
      if (payload.type === "error") {
        setStreamError(payload.message);
        setStreamLoading(false);
        closeStream();
        return;
      }
      if (payload.type === "done") {
        setStreamLoading(false);
        setStreamStatus("执行完成");
        closeStream();
        router.refresh();
      }
    };

    source.onerror = () => {
      setStreamError("流式连接已中断，请稍后重试。");
      setStreamLoading(false);
      closeStream();
    };
  }

  async function handleCreateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const title = projectTitleInput.trim();
    const summary = projectSummaryInput.trim();
    if (!title) {
      setProjectCreateError("请先输入课题标题。");
      return;
    }

    try {
      setProjectCreateLoading(true);
      setProjectCreateError(null);
      const nextProject = await createProject({ title, summary: summary || undefined });
      try {
        await investigateProject(nextProject.id);
      } catch {
        // 项目已创建成功，若首轮调查失败，允许用户在工作区手动重试。
      }
      setProjectDialogOpen(false);
      setProjectTitleInput("");
      setProjectSummaryInput("");
      startTransition(() => {
        router.push(`/workspace?projectId=${nextProject.id}`);
      });
    } catch {
      setProjectCreateError("创建课题失败，请稍后重试。");
    } finally {
      setProjectCreateLoading(false);
    }
  }

  async function handleInvestigateCurrentProject() {
    if (!workbench) return;
    try {
      setInvestigationLoading(true);
      await investigateProject(workbench.project.id);
      router.refresh();
    } finally {
      setInvestigationLoading(false);
    }
  }

  async function handleDeleteProject(projectId: string) {
    const confirmed = window.confirm("删除后当前项目及其成果会立即消失。确定继续吗？");
    if (!confirmed) return;
    await deleteProject(projectId);
    const isActive = project?.id === projectId;
    if (isActive) {
      startTransition(() => {
        router.push("/projects");
        router.refresh();
      });
      return;
    }
    router.refresh();
  }

  return (
    <main className="page-shell" data-view={activeView}>
      <div className="page-bg-orb orb-one" />
      <div className="page-bg-orb orb-two" />

      <div className="dashboard-frame" data-view={activeView}>
        <DashboardTopbar
          title={headerCopy.title}
          description={headerCopy.description}
          badges={headerCopy.badges}
          showDetailToggle={activeView !== "projects"}
          detailPanelOpen={detailPanelOpen}
          onToggleDetailPanel={() => setDetailPanelOpen((current) => !current)}
        />

        <DashboardPageNav activeView={activeView} isRouting={isRouting} onNavigate={navigateToView} />

        {pageErrors.length ? (
          <div className="page-banner-stack">
            {pageErrors.map((item) => (
              <div className="error-box page-error-box" key={item}>
                {item}
              </div>
            ))}
          </div>
        ) : null}

        <div
          className="workspace-grid"
          data-detail-panel={detailPanelOpen ? "open" : "collapsed"}
          data-view={activeView}
        >
          <ProjectSidebar
            activeView={activeView}
            projects={projects as ApiProject[]}
            activeProjectId={project?.id}
            isRouting={isRouting}
            onCreateProject={() => setProjectDialogOpen(true)}
            onSelectProject={navigateToProject}
          />

          <WorkspaceMainPanel
            activeView={activeView}
            activeViewTitle={activeViewMeta.title}
            activeViewDescription={activeViewMeta.description}
            activeViewIcon={activeViewMeta.icon}
            projects={projects as ApiProject[]}
            project={project ? { id: project.id, title: project.title, summary: project.summary, lastSync: project.lastSync } : null}
            researchState={workbench?.research_state ?? null}
            currentStage={headerCopy.currentStage}
            cards={cards}
            knowledgeCards={knowledgeCards}
            knowledgeHits={knowledgeHits}
            knowledgeQuery={knowledgeQuery}
            workflowSteps={workbench?.workflow_steps ?? []}
            agentTasks={workbench?.agent_tasks ?? []}
            roles={roles}
            pulse={pulse}
            resultSummary={resultSummary}
            selectedCardId={selectedCardId}
            summaryLoading={summaryLoading}
            investigationLoading={investigationLoading}
            generatedDocuments={generatedDocuments}
            emptyStateCopy={emptyStateMeta}
            projectTitleInput={projectTitleInput}
            projectSummaryInput={projectSummaryInput}
            projectCreateLoading={projectCreateLoading}
            projectCreateError={projectCreateError}
            onSelectCard={setSelectedCardId}
            onNavigateToProjects={() => navigateToView("projects")}
            onRunRole={handleRunRole}
            onOpenCreateProject={() => setProjectDialogOpen(true)}
            onNavigateToKnowledge={() => navigateToView("knowledge")}
            onRefreshSummary={handleRefreshSummary}
            onRunInvestigation={handleInvestigateCurrentProject}
            onProjectTitleChange={setProjectTitleInput}
            onProjectSummaryChange={setProjectSummaryInput}
            onProjectSubmit={handleCreateProject}
            onSelectProject={navigateToProject}
            onDeleteProject={handleDeleteProject}
            onKnowledgeQueryChange={setKnowledgeQuery}
            onSearchKnowledge={handleSearchKnowledge}
            pdfUploadLoading={pdfUploadLoading}
            pdfUploadError={pdfUploadError}
            hasBlockingError={hasBlockingError}
            followUpQuestion={followUpQuestion}
            followUpLoading={followUpLoading}
            followUpError={followUpError}
            followUpResult={followUpResult}
            onFollowUpQuestionChange={setFollowUpQuestion}
            onSubmitFollowUp={handleSubmitFollowUp}
            onUploadPdf={handleUploadPdf}
          />

          {activeView !== "projects" && activeView !== "results" && detailPanelOpen ? (
            <DetailSidebar
              pageLabel={activeViewMeta.label}
              pageDescription={activeViewMeta.description}
              projectId={project?.id}
              projectTitle={project?.title}
              projectSummary={project?.summary}
              stageLabel={project ? headerCopy.currentStage.label : undefined}
              stageDescription={project ? headerCopy.currentStage.description : undefined}
              selectedCard={selectedCard}
              summaryContent={summaryState?.content}
              generatedDocuments={generatedDocuments}
              runtimeHealth={runtimeHealth}
              researchState={workbench?.research_state ?? null}
              knowledgeCount={knowledgeCards.length}
              taskCount={workbench?.agent_tasks.length ?? 0}
            />
          ) : null}
        </div>
      </div>

      <CreateProjectDialog
        open={projectDialogOpen}
        titleInput={projectTitleInput}
        summaryInput={projectSummaryInput}
        loading={projectCreateLoading}
        error={projectCreateError}
        onOpenChange={setProjectDialogOpen}
        onTitleChange={setProjectTitleInput}
        onSummaryChange={setProjectSummaryInput}
        onSubmit={handleCreateProject}
      />

      <RoleRunDialog
        open={modalOpen}
        activeRole={activeRole}
        loading={streamLoading}
        status={streamStatus}
        error={streamError}
        content={streamContent}
        meta={streamMeta}
        onOpenChange={(open) => {
          setModalOpen(open);
          if (!open) {
            closeStream();
          }
        }}
      />
    </main>
  );
}
