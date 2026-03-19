import { FolderKanban, Plus } from "lucide-react";
import type { ApiProject } from "@/lib/api";
import { getStageLabel } from "./content";
import type { DashboardView } from "./types";

type ProjectSidebarProps = {
  activeView: DashboardView;
  projects: ApiProject[];
  activeProjectId?: string;
  isRouting: boolean;
  onCreateProject: () => void;
  onSelectProject: (projectId: string) => void;
};

export function ProjectSidebar({
  activeView,
  projects,
  activeProjectId,
  isRouting,
  onCreateProject,
  onSelectProject,
}: ProjectSidebarProps) {
  if (activeView === "projects") {
    return (
      <aside className="sidebar-panel">
        <div className="info-stack detail-info-stack">
          <article className="info-card">
            <span>项目原则</span>
            <strong>一个课题，对应一套独立知识与工作流</strong>
            <p>题目决定边界，说明决定 PI 的拆解方式。后续成果、知识库和角色执行都围绕这份输入展开。</p>
          </article>
          <article className="info-card">
            <span>建议填写</span>
            <strong>题目 + 研究背景 + 你最想回答的问题</strong>
            <p>这会直接影响文献检索词、研究焦点、缺口判断与方案生成，不要只写一个模糊方向。</p>
          </article>
          <button className="primary-button" onClick={onCreateProject} type="button">
            <Plus size={16} />
            立即新建
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside className="sidebar-panel">
      <div className="panel-head">
        <div>
          <span className="mini-label">
            <FolderKanban size={14} />
            项目管理
          </span>
          <h2>当前课题</h2>
        </div>
        <button className="icon-button" onClick={onCreateProject} type="button">
          <Plus size={16} />
          新建
        </button>
      </div>

      <div className="project-list">
        {projects.length ? (
          projects.map((item) => {
            const isActive = item.id === activeProjectId;
            return (
              <button
                key={item.id}
                className={`project-switcher ${isActive ? "is-active" : ""}`}
                disabled={isActive || isRouting}
                onClick={() => onSelectProject(item.id)}
                type="button"
              >
                <div className="project-switcher-head">
                  <strong>{item.title}</strong>
                  <span className={`badge ${isActive ? "solid" : "ghost"}`}>
                    {getStageLabel(item.stage)}
                  </span>
                </div>
                <p>{item.summary ?? "还没有补充课题说明，可以先写一个简要研究背景。"}</p>
              <span className="project-switcher-foot">{isActive ? "当前项目" : "切换到这个课题"}</span>
            </button>
          );
        })
      ) : (
          <div className="empty-state">当前还没有任何项目。先新建一个真实课题，再进入工作区推进研究。</div>
      )}
      </div>
    </aside>
  );
}
