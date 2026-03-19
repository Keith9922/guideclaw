import {
  getProjectsStrict,
  getResultSummaryStrict,
  getRuntimeHealthStrict,
  getWorkbenchDataStrict,
  type ApiProject,
  type ResultSummary,
  type RuntimeHealth,
  type WorkbenchData,
} from "@/lib/api";

export type DashboardView = "workspace" | "artifacts" | "knowledge" | "roles" | "projects" | "results";

export type WorkspacePageData = {
  projects: ApiProject[];
  activeProjectId: string | null;
  workbench: WorkbenchData | null;
  resultSummary: ResultSummary | null;
  runtimeHealth: RuntimeHealth | null;
  pageErrors: string[];
  hasBlockingError: boolean;
};

function formatPageError(label: string, error: unknown): string {
  if (error && typeof error === "object" && "message" in error && typeof error.message === "string") {
    return `${label}：${error.message}`;
  }
  return `${label}：发生未知错误，请检查本地 API 与 OpenClaw 运行状态。`;
}

export async function getWorkspacePageData(requestedProjectId?: string): Promise<WorkspacePageData> {
  const pageErrors: string[] = [];

  const [projectsResult, runtimeHealthResult] = await Promise.allSettled([
    getProjectsStrict(),
    getRuntimeHealthStrict(),
  ]);

  const projects = projectsResult.status === "fulfilled" ? projectsResult.value : [];
  if (projectsResult.status === "rejected") {
    pageErrors.push(formatPageError("项目列表加载失败", projectsResult.reason));
  }

  const runtimeHealth = runtimeHealthResult.status === "fulfilled" ? runtimeHealthResult.value : null;
  if (runtimeHealthResult.status === "rejected") {
    pageErrors.push(formatPageError("运行状态检查失败", runtimeHealthResult.reason));
  }

  let activeProjectId = requestedProjectId
    ? projects.length
      ? projects.some((project) => project.id === requestedProjectId)
        ? requestedProjectId
        : null
      : requestedProjectId
    : projects[0]?.id ?? null;

  if (requestedProjectId && projects.length && !activeProjectId) {
    pageErrors.push(`请求的项目 ${requestedProjectId} 不存在，可能已被删除或链接已失效。`);
  }

  let workbench: WorkbenchData | null = null;
  let resultSummary: ResultSummary | null = null;
  if (activeProjectId) {
    try {
      workbench = await getWorkbenchDataStrict(activeProjectId);
    } catch (error) {
      pageErrors.push(formatPageError(`项目 ${activeProjectId} 工作区加载失败`, error));
    }
    try {
      resultSummary = await getResultSummaryStrict(activeProjectId);
    } catch (error) {
      pageErrors.push(formatPageError(`项目 ${activeProjectId} 结果汇总加载失败`, error));
    }
  }

  return {
    projects,
    activeProjectId,
    workbench,
    resultSummary,
    runtimeHealth,
    pageErrors,
    hasBlockingError: pageErrors.length > 0 && !workbench,
  };
}
