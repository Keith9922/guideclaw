import { DashboardShell } from "@/components/dashboard-shell";
import { getWorkspacePageData } from "@/lib/page-data";

type PageProps = {
  searchParams?: Promise<{
    projectId?: string | string[];
  }>;
};

export default async function ArtifactsPage({ searchParams }: PageProps) {
  const params = (await searchParams) ?? {};
  const requestedProjectId = Array.isArray(params.projectId) ? params.projectId[0] : params.projectId;
  const { projects, workbench, resultSummary, runtimeHealth, pageErrors, hasBlockingError } =
    await getWorkspacePageData(requestedProjectId);

  return (
    <DashboardShell
      activeView="artifacts"
      projects={projects}
      workbench={workbench}
      resultSummary={resultSummary}
      llmSummary={null}
      runtimeHealth={runtimeHealth}
      pageErrors={pageErrors}
      hasBlockingError={hasBlockingError}
    />
  );
}
