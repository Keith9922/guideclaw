import { OverviewShell } from "@/components/overview-shell";
import { getProjectsStrict, type ApiProject } from "@/lib/api";

export default async function Page() {
  let projects: ApiProject[] = [];
  let pageErrors: string[] = [];

  try {
    projects = await getProjectsStrict();
  } catch (error) {
    pageErrors = [
      error instanceof Error
        ? `项目列表加载失败：${error.message}`
        : "项目列表加载失败：请检查本地 API 是否已启动。",
    ];
  }

  return <OverviewShell projects={projects} pageErrors={pageErrors} />;
}
