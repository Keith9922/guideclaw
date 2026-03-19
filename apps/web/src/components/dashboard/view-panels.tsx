import * as Tabs from "@radix-ui/react-tabs";
import type { FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import {
  ArrowRight,
  Bot,
  FileSearch,
  FileText,
  FolderKanban,
  LibraryBig,
  Link2,
  LoaderCircle,
  Plus,
  Search,
  SearchCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import remarkGfm from "remark-gfm";
import type {
  AgentTask,
  ApiProject,
  FollowUpResult,
  KnowledgeHit,
  ProjectResearchState,
  ResultSummary,
  WorkflowStep,
} from "@/lib/api";
import {
  buildAgentBoardTasks,
  buildWorkflowTimeline,
  categoryLabels,
  getKnowledgeMeta,
  getRoleIcon,
  getStageLabel,
  projectEntryHighlights,
  viewLabels,
} from "./content";
import type {
  DashboardView,
  EmptyViewMeta,
  InsightCard,
  InsightCategory,
  KnowledgeCard,
  ProjectPulse,
  RoleCard,
  StoredDocument,
  WorkflowTimelineItem,
} from "./types";
import { markdownComponents } from "./content";
import { TranslatableText } from "./translatable-text";

type WorkspaceViewProps = {
  activeView: DashboardView;
  activeViewTitle: string;
  activeViewDescription: string;
  activeViewIcon: typeof Sparkles;
  projects: ApiProject[];
  project:
    | {
        id: string;
        title: string;
        summary: string;
        lastSync: string;
      }
    | null;
  researchState: ProjectResearchState | null;
  resultSummary: ResultSummary | null;
  currentStage: {
    label: string;
    description: string;
  };
  cards: InsightCard[];
  knowledgeCards: KnowledgeCard[];
  knowledgeHits: KnowledgeHit[];
  knowledgeQuery: string;
  workflowSteps: WorkflowStep[];
  agentTasks: AgentTask[];
  roles: RoleCard[];
  pulse: ProjectPulse | null;
  selectedCardId: string;
  summaryLoading: boolean;
  investigationLoading: boolean;
  generatedDocuments: StoredDocument[];
  emptyStateCopy: EmptyViewMeta;
  projectTitleInput: string;
  projectSummaryInput: string;
  projectCreateLoading: boolean;
  projectCreateError: string | null;
  onSelectCard: (cardId: string) => void;
  onNavigateToProjects: () => void;
  onRunRole: (role: RoleCard) => void;
  onOpenCreateProject: () => void;
  onNavigateToKnowledge: () => void;
  onRefreshSummary: () => void;
  onRunInvestigation: () => void;
  onProjectTitleChange: (value: string) => void;
  onProjectSummaryChange: (value: string) => void;
  onProjectSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onSelectProject: (projectId: string) => void;
  onDeleteProject: (projectId: string) => void;
  onKnowledgeQueryChange: (value: string) => void;
  onSearchKnowledge: () => void;
  pdfUploadLoading: boolean;
  pdfUploadError: string | null;
  hasBlockingError?: boolean;
  followUpQuestion: string;
  followUpLoading: boolean;
  followUpError: string | null;
  followUpResult: FollowUpResult | null;
  onFollowUpQuestionChange: (value: string) => void;
  onSubmitFollowUp: () => void;
  onUploadPdf: (file: File) => void;
};

function EmptyViewAction({
  title,
  description,
  actionLabel,
  onClick,
}: {
  title: string;
  description: string;
  actionLabel: string;
  onClick: () => void;
}) {
  return (
    <div className="empty-state empty-state-large empty-state-dashed">
      <strong>{title}</strong>
      <p>{description}</p>
      <button className="primary-button" onClick={onClick} type="button">
        <FolderKanban size={16} />
        {actionLabel}
      </button>
    </div>
  );
}

function ProjectComposer({
  titleInput,
  summaryInput,
  loading,
  error,
  onTitleChange,
  onSummaryChange,
  onSubmit,
}: {
  titleInput: string;
  summaryInput: string;
  loading: boolean;
  error: string | null;
  onTitleChange: (value: string) => void;
  onSummaryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <section className="section-panel panel-soft">
      <div className="section-head">
        <div>
          <span className="mini-label">
            <Plus size={14} />
            新课题入口
          </span>
          <h2>创建一个真实研究项目</h2>
        </div>
        <p>题目和相关说明会成为 PI 编排、知识检索、成果沉淀和角色执行的共同上下文。</p>
      </div>

      <form className="composer-form" onSubmit={onSubmit}>
        <label className="project-field">
          <span>研究题目</span>
          <input
            placeholder="例如：机器学习辅助 OLED 材料筛选"
            value={titleInput}
            onChange={(event) => onTitleChange(event.target.value)}
          />
        </label>

        <label className="project-field">
          <span>相关说明</span>
          <textarea
            placeholder="补充研究背景、你已知的现状、想优先回答的问题。系统会围绕这些真实输入建立第一轮知识库和成果。"
            rows={8}
            value={summaryInput}
            onChange={(event) => onSummaryChange(event.target.value)}
          />
        </label>

        {error ? <div className="error-box">{error}</div> : null}

        <div className="project-form-actions">
          <button className="primary-button" disabled={loading} type="submit">
            {loading ? <LoaderCircle className="spin" size={16} /> : <Plus size={16} />}
            {loading ? "创建并调查中..." : "创建项目并启动首轮调查"}
          </button>
        </div>
      </form>
    </section>
  );
}

function ProjectLibrary({
  projects,
  activeProjectId,
  onSelectProject,
  onDeleteProject,
}: {
  projects: ApiProject[];
  activeProjectId?: string;
  onSelectProject: (projectId: string) => void;
  onDeleteProject: (projectId: string) => void;
}) {
  if (!projects.length) {
    return (
      <div className="empty-state empty-state-subtle">
        <strong>当前还没有任何项目</strong>
        <p>这是预期行为。等你输入真实课题后，工作区、知识库和成果页才会一起激活。</p>
      </div>
    );
  }

  return (
    <div className="project-library-grid">
      {projects.map((item) => {
        const isActive = item.id === activeProjectId;
        return (
          <article key={item.id} className={`project-library-card ${isActive ? "is-active" : ""}`}>
            <div className="project-switcher-head">
              <strong>{item.title}</strong>
              <span className={`badge ${isActive ? "solid" : "ghost"}`}>{getStageLabel(item.stage)}</span>
            </div>
            <p>{item.summary ?? "尚未填写课题说明。"}</p>
            <div className="project-library-actions">
              <button className="secondary-button" onClick={() => onSelectProject(item.id)} type="button">
                {isActive ? "当前项目" : "进入工作区"}
              </button>
              <button
                aria-label={`删除项目 ${item.title}`}
                className="icon-button icon-button-danger"
                onClick={() => onDeleteProject(item.id)}
                type="button"
              >
                <Trash2 size={16} />
                删除
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function WorkspaceHero({
  project,
  researchState,
  pulse,
  currentStage,
  summaryLoading,
  investigationLoading,
  onNavigateToKnowledge,
  onRefreshSummary,
  onRunInvestigation,
}: Pick<
  WorkspaceViewProps,
  | "project"
  | "researchState"
  | "pulse"
  | "currentStage"
  | "summaryLoading"
  | "investigationLoading"
  | "onNavigateToKnowledge"
  | "onRefreshSummary"
  | "onRunInvestigation"
>) {
  const keyQuestions = researchState?.key_questions.slice(0, 4) ?? [];
  const searchQueries = researchState?.search_queries.slice(0, 4) ?? [];
  return (
    <section className="workspace-hero">
      <div className="workspace-hero-copy">
        <span className="mini-label">
          <Sparkles size={14} />
          研究主舞台
        </span>
        <h2>{project?.title}</h2>
        <p>{currentStage.description}</p>
        <div className="hero-focus-card">
          <span>PI 当前聚焦</span>
          <strong>{pulse?.focus ?? "等待 PI 定义研究焦点"}</strong>
          <p>{researchState?.current_hypothesis ?? "当前还没有形成清晰假设，先从首轮调查建立领域地图。"}</p>
        </div>
        <div className="hero-meta">
          <span className="badge solid">{currentStage.label}</span>
          <span className="badge ghost">{pulse?.provider ?? "等待知识源"}</span>
          <span className="badge ghost">最近同步 {project?.lastSync}</span>
        </div>
        <div className="hero-column-grid">
          <article className="hero-list-block">
            <span>PI 拆出的关键问题</span>
            {keyQuestions.length ? (
              <ul>
                {keyQuestions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>系统还没有拆出关键问题，重新执行整条工作流即可生成。</p>
            )}
          </article>
          <article className="hero-list-block">
            <span>优先检索词</span>
            {searchQueries.length ? (
              <div className="tag-row">
                {searchQueries.map((item) => (
                  <span key={item} className="tag-chip">
                    {item}
                  </span>
                ))}
              </div>
            ) : (
              <p>等 PI 生成首轮检索计划后，这里会展示检索词。</p>
            )}
          </article>
        </div>
        <div className="hero-actions">
          <button className="primary-button" onClick={onRunInvestigation} disabled={investigationLoading} type="button">
            {investigationLoading ? <LoaderCircle className="spin" size={16} /> : <SearchCheck size={16} />}
            {investigationLoading ? "调查中..." : "重新执行整条工作流"}
          </button>
          <button className="secondary-button" onClick={onRefreshSummary} disabled={summaryLoading} type="button">
            {summaryLoading ? <LoaderCircle className="spin" size={16} /> : <Sparkles size={16} />}
            {summaryLoading ? "刷新中..." : "刷新研究摘要"}
          </button>
          <button className="ghost-button" onClick={onNavigateToKnowledge} type="button">
            <FileSearch size={16} />
            打开知识库并上传 PDF
          </button>
        </div>
      </div>

      <div className="workspace-hero-side">
        <article className="metric-card metric-card-strong">
          <span>为何现在做</span>
          <strong>{pulse?.whyNow ?? "等待 PI 定义本轮调查动机"}</strong>
        </article>
        <article className="metric-card">
          <span>优先缺口</span>
          <strong>{pulse?.recommendedGap ?? "等待缺口判断"}</strong>
        </article>
        <article className="metric-card">
          <span>当前假设</span>
          <strong>{researchState?.current_hypothesis ?? "等待方案设计师收口"}</strong>
        </article>
        <article className="metric-card">
          <span>下一步</span>
          <strong>{pulse?.nextStep ?? "等待调查结果"}</strong>
        </article>
      </div>
    </section>
  );
}

function ResearchCommandDeck({
  researchState,
  pulse,
}: {
  researchState: ProjectResearchState | null;
  pulse: ProjectPulse | null;
}) {
  return (
    <section className="section-panel section-nested">
      <div className="section-head">
        <div>
          <span className="mini-label">
            <Sparkles size={14} />
            PI 编排单
          </span>
          <h2>这一轮工作流到底在解决什么</h2>
        </div>
        <p>真正的中轴是研究焦点、当前假设、下一步和证据来源，不是单纯把几个 Agent 摆在一起。</p>
      </div>

      <div className="command-deck">
        <article className="command-card command-card-strong">
          <span>研究焦点</span>
          <strong>{researchState?.research_focus ?? "等待 PI 给出当前焦点"}</strong>
          <p>{researchState?.why_now ?? "等首轮调查后，这里会解释为什么这个方向值得现在做。"}</p>
        </article>
        <article className="command-card">
          <span>当前假设</span>
          <strong>{researchState?.current_hypothesis ?? "等待方案设计师生成首轮可讨论假设"}</strong>
          <p>这张卡应该能直接被拿去和导师或组会讨论，而不是停留在概念层。</p>
        </article>
        <article className="command-card">
          <span>下一步动作</span>
          <strong>{pulse?.nextStep ?? "等待组会秘书沉淀行动项"}</strong>
          <p>{researchState?.provider_note ?? "还没有形成外部文献来源说明。"}</p>
        </article>
      </div>
    </section>
  );
}

function AgentOrchestra({
  tasks,
  roles,
  onRunRole,
}: {
  tasks: AgentTask[];
  roles: RoleCard[];
  onRunRole: (role: RoleCard) => void;
}) {
  const boardTasks = buildAgentBoardTasks(tasks);
  return (
    <section className="section-panel section-nested">
      <div className="section-head">
        <div>
          <span className="mini-label">
            <Bot size={14} />
            PI 编排与 Agent 分发
          </span>
          <h2>主流程不是聊天，而是任务接力</h2>
        </div>
        <p>PI 先定义焦点和问题，再把任务分发给文献助理、选题分析员、方案设计师和组会秘书。</p>
      </div>

      <div className="agent-board">
        {boardTasks.map((task) => {
          const role = roles.find((item) => item.id === task.role);
          const Icon = getRoleIcon(task.role);
          return (
            <article
              key={task.id}
              className={`agent-board-card is-${task.status} ${task.isPrimary ? "is-primary-task" : ""}`}
            >
              <div className="agent-board-header">
                <span className="mini-label">
                  <Icon size={14} />
                  {task.role === "principal_investigator" ? "PI" : "Agent"}
                </span>
                <span className={`badge ${task.status === "completed" ? "solid" : "ghost"}`}>
                  {task.status === "completed" ? "已完成" : task.status}
                </span>
              </div>
              <h3>{task.role === "principal_investigator" ? "PI" : task.roleName}</h3>
              <strong>{task.title}</strong>
              <p>{task.objective}</p>
              <div className="agent-board-meta">
                <span>输入：{task.inputs.length}</span>
                <span>证据源：{task.evidence_source_ids.length}</span>
                <span>成果：{task.artifact_ids.length}</span>
              </div>
              {task.output_summary ? <div className="agent-board-summary">{task.output_summary}</div> : null}
              {role ? (
                <button className="ghost-button" onClick={() => onRunRole(role)} type="button">
                  <ArrowRight size={16} />
                  让这个角色继续执行
                </button>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function FeaturedArtifacts({
  projectId,
  cards,
  selectedCardId,
  onSelectCard,
}: {
  projectId?: string;
  cards: InsightCard[];
  selectedCardId: string;
  onSelectCard: (cardId: string) => void;
}) {
  if (!cards.length) {
    return (
      <div className="empty-state empty-state-dashed">
        当前还没有成果卡。先执行首轮调查，再回来查看结构化结果。
      </div>
    );
  }

  return (
    <div className="artifact-preview-shell">
      <div className="artifact-preview-head">
        <p>工作区只展示摘要。点击任一卡片，右侧会展开完整内容与证据片段。</p>
      </div>
      <div className="artifact-scroller">
        {cards.map((card) => (
        <button
          key={card.id}
          className={`artifact-card artifact-card-compact ${selectedCardId === card.id ? "is-selected" : ""}`}
          onClick={() => onSelectCard(card.id)}
          type="button"
        >
          <div className="artifact-head">
            <span className="badge ghost">{categoryLabels[card.category]}</span>
            <span>{card.status}</span>
          </div>
          <TranslatableText as="h3" className="artifact-title" projectId={projectId} text={card.title} />
          <TranslatableText as="p" className="artifact-summary" projectId={projectId} text={card.summary} />
          <div className="artifact-evidence-summary">
            <span className="badge ghost">{card.evidence.length} 条引用</span>
            {card.evidence[0]?.url ? (
              <a
                className="text-link"
                href={card.evidence[0].url}
                onClick={(event) => event.stopPropagation()}
                rel="noreferrer"
                target="_blank"
              >
                <Link2 size={14} />
                原始来源
              </a>
            ) : null}
          </div>
          <div className="tag-row tag-row-compact">
            {card.tags.slice(0, 2).map((tag) => (
              <span key={tag} className="tag-chip">
                {tag}
              </span>
            ))}
            {card.tags.length > 2 ? <span className="tag-chip tag-chip-muted">+{card.tags.length - 2}</span> : null}
          </div>
        </button>
        ))}
      </div>
    </div>
  );
}

function DocumentArchiveSection({
  documents,
  compact = false,
}: {
  documents: StoredDocument[];
  compact?: boolean;
}) {
  if (!documents.length) {
    return (
      <div className="empty-state empty-state-dashed">
        当前还没有持久化文档。执行首轮调查、刷新研究摘要或触发角色运行后，这里会自动沉淀 Markdown 记录。
      </div>
    );
  }

  const visibleDocuments = compact ? documents.slice(0, 3) : documents;

  return (
    <section className="section-panel section-nested">
      <div className="section-head">
        <div>
          <span className="mini-label">
            <FileText size={14} />
            文档档案
          </span>
          <h2>已持久化的 Markdown 记录</h2>
        </div>
        <p>每次研究摘要、首轮调查和角色执行的输出都会入库，方便后续翻阅、对照和复用。</p>
      </div>

      <div className="document-archive-list">
        {visibleDocuments.map((item) => (
          <details className="document-archive-item" key={item.id}>
            <summary className="document-archive-summary">
              <div>
                <strong>{item.title}</strong>
                <p>{new Date(item.updated_at).toLocaleString("zh-CN")}</p>
              </div>
              <div className="runtime-badges">
                <span className="badge ghost">
                  {item.doc_type === "project_summary"
                    ? "研究摘要"
                    : item.doc_type === "follow_up"
                      ? "追问结果"
                      : item.doc_type === "result_summary"
                        ? "结果汇总"
                      : "角色执行"}
                </span>
                {item.role ? <span className="badge ghost">{item.role}</span> : null}
                <span className="badge ghost">{item.source === "system" ? "系统沉淀" : item.source === "openclaw" ? "OpenClaw" : "OpenRouter"}</span>
              </div>
            </summary>
            <div className="document-archive-body">
              <div className="markdown-box markdown-light markdown-tall">
                <ReactMarkdown components={markdownComponents()} remarkPlugins={[remarkGfm]}>
                  {item.content}
                </ReactMarkdown>
              </div>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}

function KnowledgeDigest({ knowledgeCards }: { knowledgeCards: KnowledgeCard[] }) {
  const meta = getKnowledgeMeta(knowledgeCards);
  return (
    <section className="section-panel section-nested">
      <div className="section-head">
        <div>
          <span className="mini-label">
            <LibraryBig size={14} />
            知识库入口
          </span>
          <h2>引用源与可打开链接</h2>
        </div>
        <p>文献助理搜到的论文，会优先带 DOI、引用和外部链接，避免只剩一段模型总结。</p>
      </div>
      <div className="knowledge-metrics">
        <article className="metric-card">
          <span>候选来源</span>
          <strong>{meta.total}</strong>
        </article>
        <article className="metric-card">
          <span>带原始链接</span>
          <strong>{meta.withLinks}</strong>
        </article>
        <article className="metric-card">
          <span>带摘要</span>
          <strong>{meta.withAbstract}</strong>
        </article>
      </div>
      <div className="artifact-preview-head">
        <p>这里只放可快速浏览的知识源摘要。正文级检索、PDF 解析和更多来源请去知识库页。</p>
      </div>
      <div className="knowledge-scroller">
        {knowledgeCards.slice(0, 4).map((source) => (
          <article key={source.id} className="knowledge-card knowledge-card-compact">
            <div className="knowledge-card-head">
              <span className="badge ghost">{source.label}</span>
              <span>{source.year ?? "未知年份"}</span>
            </div>
            <TranslatableText as="h3" className="knowledge-title" projectId={source.project_id} text={source.title} />
            <TranslatableText
              as="p"
              className="knowledge-summary"
              projectId={source.project_id}
              text={source.abstract ?? source.citation ?? "暂无摘要"}
            />
            <div className="knowledge-card-footer">
              <span>{source.venue ?? "未知来源"}</span>
              {source.url ? (
                <a className="text-link" href={source.url} rel="noreferrer" target="_blank">
                  <Link2 size={14} />
                  打开原始来源
                </a>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function FollowUpSection({
  projectId,
  followUpQuestion,
  followUpLoading,
  followUpError,
  followUpResult,
  onFollowUpQuestionChange,
  onSubmitFollowUp,
}: {
  projectId: string;
  followUpQuestion: string;
  followUpLoading: boolean;
  followUpError: string | null;
  followUpResult: FollowUpResult | null;
  onFollowUpQuestionChange: (value: string) => void;
  onSubmitFollowUp: () => void;
}) {
  return (
    <section className="section-panel section-nested">
      <div className="section-head">
        <div>
          <span className="mini-label">
            <Sparkles size={14} />
            继续追问
          </span>
          <h2>基于当前项目，让 PI 再推进一轮</h2>
        </div>
        <p>适合你已经完成首轮调查后，继续问一个更具体的问题。PI 会先判断，再优先分派最关键的 1 个子 Agent 继续执行。</p>
      </div>

      <div className="follow-up-composer">
        <textarea
          className="follow-up-textarea"
          placeholder="例如：如果我只想做本科毕设，应该优先从数据集构建、单性质预测还是多性质联合预测切入？"
          rows={4}
          value={followUpQuestion}
          onChange={(event) => onFollowUpQuestionChange(event.target.value)}
        />
        <div className="project-form-actions project-inline-actions">
          <button className="primary-button" disabled={followUpLoading || !followUpQuestion.trim()} onClick={onSubmitFollowUp} type="button">
            {followUpLoading ? <LoaderCircle className="spin" size={16} /> : <ArrowRight size={16} />}
            {followUpLoading ? "PI 正在调度..." : "开始追问"}
          </button>
        </div>
      </div>

      {followUpError ? <div className="error-box">{followUpError}</div> : null}

      {followUpResult ? (
        <div className="follow-up-result">
          <div className="follow-up-meta">
            <article className="command-card command-card-strong">
              <span>PI 本轮聚焦</span>
              <strong>{followUpResult.pi_focus}</strong>
              <p>这次追问围绕这个重点继续往下拆，不需要重新从头做首轮调查。</p>
            </article>
            <article className="command-card">
              <span>本轮分派</span>
              <div className="tag-row">
                {followUpResult.delegates.length ? (
                  followUpResult.delegates.map((item) => (
                    <span className="tag-chip" key={`${item.role}-${item.objective}`}>
                      {item.role}
                    </span>
                  ))
                ) : (
                  <span className="tag-chip tag-chip-muted">PI 直接回答</span>
                )}
              </div>
              <p>{followUpResult.question}</p>
            </article>
          </div>

          <div className="markdown-box markdown-light">
            <ReactMarkdown components={markdownComponents()} remarkPlugins={[remarkGfm]}>
              {followUpResult.content}
            </ReactMarkdown>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function WorkflowExplainPanel({ workflowTimeline }: { workflowTimeline: WorkflowTimelineItem[] }) {
  return (
    <section className="section-panel section-nested">
      <div className="section-head">
        <div>
          <span className="mini-label">
            <Bot size={14} />
            交接轨迹
          </span>
          <h2>从 PI 到纪要的完整链路</h2>
        </div>
        <p>这是系统真正的工作流轨迹，不是单个角色各自说一段话。</p>
      </div>

      {workflowTimeline.length ? (
        <div className="workflow-vertical">
          {workflowTimeline.map((step) => (
            <article key={`${step.role}-${step.index}`} className="workflow-vertical-card">
              <div className="workflow-vertical-index">{step.index}</div>
              <div className="workflow-vertical-body">
                <div className="workflow-vertical-head">
                  <strong>{step.roleName}</strong>
                  <span className="badge ghost">{step.title}</span>
                </div>
                <p>{step.summary}</p>
                <span className="workflow-handoff">{step.handoffLabel}</span>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state empty-state-dashed">
          还没有协作轨迹。先创建项目并执行首轮调查。
        </div>
      )}
    </section>
  );
}

function ArtifactSections({
  projectId,
  cards,
  selectedCardId,
  onSelectCard,
}: {
  projectId?: string;
  cards: InsightCard[];
  selectedCardId: string;
  onSelectCard: (cardId: string) => void;
}) {
  const groups: InsightCategory[] = ["literature", "gap", "plan", "meeting"];
  return (
    <div className="workspace-stack">
      {groups.map((group) => {
        const groupCards = cards.filter((card) => card.category === group);
        return (
          <section key={group} className="section-panel section-nested">
            <div className="section-head">
              <div>
                <span className="mini-label">
                  <FileText size={14} />
                  {categoryLabels[group]}
                </span>
                <h2>{categoryLabels[group]}</h2>
              </div>
              <p>{groupCards.length ? `${groupCards.length} 条结构化结果` : "当前没有这类结果"}</p>
            </div>
            {groupCards.length ? (
              <div className="card-grid">
                {groupCards.map((card) => (
                  <button
                    key={card.id}
                    className={`artifact-card ${selectedCardId === card.id ? "is-selected" : ""}`}
                    onClick={() => onSelectCard(card.id)}
                    type="button"
                  >
                    <div className="artifact-head">
                      <span className="badge ghost">{categoryLabels[card.category]}</span>
                      <span>{card.status}</span>
                    </div>
                    <TranslatableText as="h3" className="artifact-title" projectId={projectId} text={card.title} />
                    <TranslatableText as="p" className="artifact-summary" projectId={projectId} text={card.summary} />
                    <div className="artifact-evidence-summary">
                      <span className="badge ghost">{card.evidence.length} 条引用</span>
                      {card.evidence[0]?.url ? (
                        <a
                          className="text-link"
                          href={card.evidence[0].url}
                          onClick={(event) => event.stopPropagation()}
                          rel="noreferrer"
                          target="_blank"
                        >
                          <Link2 size={14} />
                          原始来源
                        </a>
                      ) : null}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="empty-state empty-state-dashed">当前没有这类成果。</div>
            )}
          </section>
        );
      })}
    </div>
  );
}

function KnowledgeSection({
  knowledgeCards,
  knowledgeHits,
  knowledgeQuery,
  onKnowledgeQueryChange,
  onSearchKnowledge,
  pdfUploadLoading,
  pdfUploadError,
  onUploadPdf,
}: {
  knowledgeCards: KnowledgeCard[];
  knowledgeHits: KnowledgeHit[];
  knowledgeQuery: string;
  onKnowledgeQueryChange: (value: string) => void;
  onSearchKnowledge: () => void;
  pdfUploadLoading: boolean;
  pdfUploadError: string | null;
  onUploadPdf: (file: File) => void;
}) {
  return (
    <div className="workspace-stack">
      <section className="section-panel section-nested">
        <div className="section-head">
          <div>
            <span className="mini-label">
              <Search size={14} />
              项目知识搜索
            </span>
            <h2>先查知识库，再让模型回答</h2>
          </div>
          <p>这是当前项目级的轻量 RAG 入口。先基于已有来源检索，再决定要不要继续跑角色。</p>
        </div>

        <div className="upload-strip">
          <label className="secondary-button upload-button">
            {pdfUploadLoading ? <LoaderCircle className="spin" size={16} /> : <FileSearch size={16} />}
            {pdfUploadLoading ? "解析 PDF 中..." : "上传 PDF 进入知识库"}
            <input
              accept="application/pdf"
              className="file-input-hidden"
              disabled={pdfUploadLoading}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  onUploadPdf(file);
                }
                event.currentTarget.value = "";
              }}
              type="file"
            />
          </label>
          <span className="upload-hint">上传后会解析文本并写入项目知识块，供后续检索与引用。</span>
        </div>
        {pdfUploadError ? <div className="error-box">{pdfUploadError}</div> : null}

        <div className="knowledge-search-row">
          <input
            className="search-input"
            placeholder="输入一个问题，例如：OLED 里常见的分子表示方法有哪些？"
            value={knowledgeQuery}
            onChange={(event) => onKnowledgeQueryChange(event.target.value)}
          />
          <button className="primary-button" onClick={onSearchKnowledge} type="button">
            <Search size={16} />
            检索项目知识
          </button>
        </div>

        {knowledgeHits.length ? (
          <div className="knowledge-hit-list">
            {knowledgeHits.map((hit) => (
              <article key={`${hit.source_id}-${hit.score}`} className="knowledge-hit-card">
                <div className="knowledge-card-head">
                  <span className="badge ghost">{hit.source_type}</span>
                  <span>相关度 {hit.score.toFixed(1)}</span>
                </div>
                <h3>{hit.title}</h3>
                <p>{hit.excerpt}</p>
                <div className="knowledge-card-footer">
                  {hit.citation ? <span>{hit.citation}</span> : <span>暂无引用串</span>}
                  {hit.url ? (
                    <a className="text-link" href={hit.url} rel="noreferrer" target="_blank">
                      <Link2 size={14} />
                      打开来源
                    </a>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state empty-state-dashed">
            先输入问题并检索；如果当前项目还没有知识源，这里也会保持空白。
          </div>
        )}
      </section>

      <section className="section-panel section-nested">
        <div className="section-head">
          <div>
            <span className="mini-label">
              <LibraryBig size={14} />
              原始知识源
            </span>
            <h2>当前项目的候选论文与原始链接</h2>
          </div>
          <p>这里展示的是项目级知识库，不是模型自己生成的虚构参考。</p>
        </div>

        <div className="knowledge-list">
          {knowledgeCards.length ? (
            knowledgeCards.map((source) => (
              <article key={source.id} className="knowledge-card">
                <div className="knowledge-card-head">
                  <span className="badge ghost">{source.label}</span>
                  <span>{source.year ?? "未知年份"}</span>
                </div>
                <h3>{source.title}</h3>
                <p>{source.abstract ?? source.citation ?? "暂无摘要"}</p>
                <div className="knowledge-card-footer">
                  <span>{source.venue ?? "未知来源"}</span>
                  <div className="knowledge-card-links">
                    {source.doi ? <span className="tag-chip">DOI {source.doi}</span> : null}
                    {source.url ? (
                      <a className="text-link" href={source.url} rel="noreferrer" target="_blank">
                        <Link2 size={14} />
                        打开来源
                      </a>
                    ) : null}
                  </div>
                </div>
              </article>
            ))
          ) : (
            <div className="empty-state empty-state-dashed">当前还没有知识源。</div>
          )}
        </div>
      </section>
    </div>
  );
}

function ResultsSummaryPanel({
  projectId,
  summary,
}: {
  projectId: string;
  summary: ResultSummary | null;
}) {
  if (!summary) {
    return (
      <div className="empty-state empty-state-dashed">
        当前还没有结果汇总。先完成首轮调查，再把项目收成最终交付物。
      </div>
    );
  }

  return (
    <div className="workspace-stack results-stack">
      <section className="section-panel results-hero-panel">
        <div className="results-hero-copy">
          <span className="mini-label">
            <Sparkles size={14} />
            结果汇总
          </span>
          <h2>{summary.project_title}</h2>
          <p>{summary.intro}</p>
          <div className="runtime-badges">
            <span className="badge solid">{summary.stage_label}</span>
            <span className="badge ghost">{summary.recommended_reading.length} 篇优先阅读</span>
            <span className="badge ghost">{summary.next_actions.length} 条行动建议</span>
          </div>
        </div>
        <div className="results-hero-actions">
          <a className="primary-button" href={summary.pdf_url} rel="noreferrer" target="_blank">
            <FileText size={16} />
            打开 / 下载 PDF
          </a>
          <a className="secondary-button" href={`/workspace?projectId=${projectId}`}>
            <ArrowRight size={16} />
            回到工作区继续推进
          </a>
        </div>
      </section>

      <section className="results-primer-grid">
        <article className="section-panel section-nested results-primer-card">
          <div className="section-head">
            <div>
              <span className="mini-label">
                <Sparkles size={14} />
                你会先搞懂什么
              </span>
              <h2>方向、问题、切入点</h2>
            </div>
          </div>
          <p>这页不是把中间过程再重复一遍，而是直接告诉你：这个方向在做什么、当前最值得关注什么、最适合从哪里开始。</p>
        </article>
        <article className="section-panel section-nested results-primer-card">
          <div className="section-head">
            <div>
              <span className="mini-label">
                <LibraryBig size={14} />
                你会拿走什么
              </span>
              <h2>阅读清单和行动清单</h2>
            </div>
          </div>
          <p>优先阅读会告诉你先看哪几篇，下一步行动会告诉你这一周该做什么，不用自己从零组织材料。</p>
        </article>
        <article className="section-panel section-nested results-primer-card">
          <div className="section-head">
            <div>
              <span className="mini-label">
                <SearchCheck size={14} />
                怎么继续推进
              </span>
              <h2>不懂就继续追问</h2>
            </div>
          </div>
          <p>如果这里还有看不懂的点，就回到工作区继续追问。PI 会基于当前项目状态，再次分派最关键的子 Agent 往下推进。</p>
        </article>
      </section>

      <section className="section-panel section-nested">
        <div className="section-head">
          <div>
            <span className="mini-label">
              <FileText size={14} />
              PDF 预览
            </span>
            <h2>浏览器内直接查看导出版本</h2>
          </div>
          <p>这里展示的就是可下载 PDF 的浏览器内渲染版本，适合直接检查排版和导出效果。</p>
        </div>
        <div className="results-pdf-frame-shell">
          <iframe className="results-pdf-frame" src={summary.pdf_url} title={`${summary.project_title} 结果汇总 PDF`} />
        </div>
      </section>

      <div className="results-grid">
        {summary.sections.map((section) => (
          <section className="section-panel section-nested results-section-card" key={section.title}>
            <div className="section-head">
              <div>
                <span className="mini-label">
                  <FileText size={14} />
                  核心结论
                </span>
                <h2>{section.title}</h2>
              </div>
            </div>
            <div className="results-section-body">
              <ReactMarkdown components={markdownComponents()} remarkPlugins={[remarkGfm]}>
                {section.content}
              </ReactMarkdown>
              {section.bullets.length ? (
                <ul className="results-bullet-list">
                  {section.bullets.map((item) => (
                    <li key={item}>
                      <TranslatableText as="span" className="results-inline-text" projectId={projectId} text={item} />
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </section>
        ))}
      </div>

      <div className="results-dual-grid">
        <section className="section-panel section-nested">
          <div className="section-head">
            <div>
              <span className="mini-label">
                <LibraryBig size={14} />
                优先阅读
              </span>
              <h2>先看这几篇</h2>
            </div>
            <p>这不是泛推荐，而是当前项目最适合科研新人建立领域地图的入口。</p>
          </div>
          <div className="results-reference-list">
            {summary.recommended_reading.length ? (
              summary.recommended_reading.map((item) => (
                <article className="results-reference-card" key={`${item.title}-${item.doi ?? item.url ?? item.reason}`}>
                  <TranslatableText as="h3" className="knowledge-title" projectId={projectId} text={item.title} />
                  <TranslatableText as="p" className="knowledge-summary" projectId={projectId} text={item.reason} />
                  <div className="knowledge-card-footer">
                    {item.citation ? <span>{item.citation}</span> : <span>暂无引用串</span>}
                    <div className="knowledge-card-links">
                      {item.doi ? <span className="tag-chip">DOI {item.doi}</span> : null}
                      {item.url ? (
                        <a className="text-link" href={item.url} rel="noreferrer" target="_blank">
                          <Link2 size={14} />
                          打开来源
                        </a>
                      ) : null}
                    </div>
                  </div>
                </article>
              ))
            ) : (
              <div className="empty-state empty-state-dashed">当前还没有可推荐的阅读列表。</div>
            )}
          </div>
        </section>

        <section className="section-panel section-nested">
          <div className="section-head">
            <div>
              <span className="mini-label">
                <SearchCheck size={14} />
                你接下来就做这个
              </span>
              <h2>行动清单</h2>
            </div>
            <p>这部分是给科研新人直接执行的，不需要你先完全搞懂所有细节。</p>
          </div>
          <div className="results-action-list">
            {summary.next_actions.length ? (
              summary.next_actions.map((item) => (
                <article className="results-action-card" key={`${item.title}-${item.description}`}>
                  <TranslatableText as="strong" className="results-action-title" projectId={projectId} text={item.title} />
                  <TranslatableText as="p" className="results-action-copy" projectId={projectId} text={item.description} />
                </article>
              ))
            ) : (
              <div className="empty-state empty-state-dashed">当前还没有下一步行动建议。</div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function RoleExecutionPanel({
  roles,
  workflowTimeline,
  onRunRole,
}: {
  roles: RoleCard[];
  workflowTimeline: WorkflowTimelineItem[];
  onRunRole: (role: RoleCard) => void;
}) {
  return (
    <div className="workspace-stack">
      <WorkflowExplainPanel workflowTimeline={workflowTimeline} />
      <section className="section-panel section-nested">
        <div className="section-head">
          <div>
            <span className="mini-label">
              <Bot size={14} />
              角色执行
            </span>
            <h2>让单个 Agent 在真实项目上下文里继续工作</h2>
          </div>
          <p>这里是 OpenClaw 的执行入口。每个角色都会读取当前项目上下文和知识源。</p>
        </div>

        <div className="roles-grid">
          {roles.map((role) => {
            const Icon = getRoleIcon(role.id);
            return (
              <article key={role.id} className={`role-card role-${role.state}`}>
                <div className="role-meta">
                  <span className="badge ghost">{role.state}</span>
                  <span className="role-progress">{role.progress}%</span>
                </div>
                <div className="role-title-row">
                  <Icon size={18} />
                  <h3>{role.name}</h3>
                </div>
                <strong>{role.title}</strong>
                <p>{role.description}</p>
                {role.outputSummary ? (
                  <div className="role-output-brief">
                    <span>{role.source === "workflow" ? `步骤 ${role.workflowIndex}` : "当前状态"}</span>
                    <p>{role.outputSummary}</p>
                  </div>
                ) : null}
                <div className="progress-track" aria-hidden="true">
                  <span style={{ width: `${role.progress}%` }} />
                </div>
                <div className="role-footer">
                  <span>{getStageLabel(role.stage)}</span>
                  <button className="ghost-button" onClick={() => onRunRole(role)} type="button">
                    运行角色
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export function WorkspaceMainPanel({
  activeView,
  activeViewTitle,
  activeViewDescription,
  activeViewIcon: ActiveViewIcon,
  projects,
  project,
  researchState,
  resultSummary,
  currentStage,
  cards,
  knowledgeCards,
  knowledgeHits,
  knowledgeQuery,
  workflowSteps,
  agentTasks,
  roles,
  pulse,
  selectedCardId,
  summaryLoading,
  investigationLoading,
  generatedDocuments,
  emptyStateCopy,
  projectTitleInput,
  projectSummaryInput,
  projectCreateLoading,
  projectCreateError,
  onSelectCard,
  onNavigateToProjects,
  onRunRole,
  onOpenCreateProject,
  onNavigateToKnowledge,
  onRefreshSummary,
  onRunInvestigation,
  onProjectTitleChange,
  onProjectSummaryChange,
  onProjectSubmit,
  onSelectProject,
  onDeleteProject,
  onKnowledgeQueryChange,
  onSearchKnowledge,
  pdfUploadLoading,
  pdfUploadError,
  hasBlockingError = false,
  followUpQuestion,
  followUpLoading,
  followUpError,
  followUpResult,
  onFollowUpQuestionChange,
  onSubmitFollowUp,
  onUploadPdf,
}: WorkspaceViewProps) {
  const workflowTimeline = buildWorkflowTimeline(workflowSteps);

  if (activeView === "projects") {
    return (
      <section className="main-column workspace-center">
        <section className="section-panel workspace-focus-panel">
          <div className="section-head">
            <div>
              <span className="mini-label">
                <ActiveViewIcon size={14} />
                {viewLabels[activeView].label}
              </span>
              <h2>{activeViewTitle}</h2>
            </div>
            <p>{activeViewDescription}</p>
          </div>

          <div className="workspace-stack">
            <div className="project-hub-grid">
              <div className="project-hub-primary">
                <ProjectComposer
                  titleInput={projectTitleInput}
                  summaryInput={projectSummaryInput}
                  loading={projectCreateLoading}
                  error={projectCreateError}
                  onTitleChange={onProjectTitleChange}
                  onSummaryChange={onProjectSummaryChange}
                  onSubmit={onProjectSubmit}
                />

                <section className="feature-grid">
                  {projectEntryHighlights.map((item) => {
                    const Icon = item.icon;
                    return (
                      <article key={item.title} className="feature-card">
                        <div className="feature-icon">
                          <Icon size={18} />
                        </div>
                        <h3>{item.title}</h3>
                        <p>{item.description}</p>
                      </article>
                    );
                  })}
                </section>
              </div>

              <section className="section-panel section-nested">
                <div className="section-head">
                  <div>
                    <span className="mini-label">
                      <FolderKanban size={14} />
                      项目池
                    </span>
                    <h2>所有研究议题的入口</h2>
                  </div>
                  <p>进入不同课题时，整个工作区、知识库和成果页都会切到对应上下文。</p>
                </div>
                <ProjectLibrary
                  projects={projects}
                  activeProjectId={project?.id}
                  onSelectProject={onSelectProject}
                  onDeleteProject={onDeleteProject}
                />
              </section>
            </div>
          </div>
        </section>
      </section>
    );
  }

  if (!project) {
    return (
      <section className="main-column workspace-center">
        <section className="section-panel workspace-focus-panel">
          <div className="section-head">
            <div>
              <span className="mini-label">
                <ActiveViewIcon size={14} />
                {viewLabels[activeView].label}
              </span>
              <h2>{activeViewTitle}</h2>
            </div>
            <p>{activeViewDescription}</p>
          </div>
          {hasBlockingError ? (
            <div className="empty-state empty-state-large empty-state-dashed">
              <strong>当前页面没有拿到有效工作区</strong>
              <p>这不是“没有成果”的正常空态，而是项目链接失效、后端不可达或工作区加载失败。</p>
              <button className="primary-button" onClick={onNavigateToProjects} type="button">
                <FolderKanban size={16} />
                回到项目管理
              </button>
            </div>
          ) : (
            <EmptyViewAction {...emptyStateCopy} onClick={onNavigateToProjects} />
          )}
        </section>
      </section>
    );
  }

  return (
    <section className="main-column workspace-center">
      <section className="section-panel workspace-focus-panel">
        <div className="section-head">
          <div>
            <span className="mini-label">
              <ActiveViewIcon size={14} />
              {viewLabels[activeView].label}
            </span>
            <h2>{activeViewTitle}</h2>
          </div>
          <p>{activeViewDescription}</p>
        </div>

        {activeView === "workspace" ? (
          <div className="workspace-stack">
            <WorkspaceHero
              project={project}
              researchState={researchState}
              pulse={pulse}
              currentStage={currentStage}
              summaryLoading={summaryLoading}
              investigationLoading={investigationLoading}
              onNavigateToKnowledge={onNavigateToKnowledge}
              onRefreshSummary={onRefreshSummary}
              onRunInvestigation={onRunInvestigation}
            />

            <ResearchCommandDeck researchState={researchState} pulse={pulse} />

            <FollowUpSection
              projectId={project.id}
              followUpQuestion={followUpQuestion}
              followUpLoading={followUpLoading}
              followUpError={followUpError}
              followUpResult={followUpResult}
              onFollowUpQuestionChange={onFollowUpQuestionChange}
              onSubmitFollowUp={onSubmitFollowUp}
            />

            <AgentOrchestra tasks={agentTasks} roles={roles} onRunRole={onRunRole} />

            <div className="workspace-dual-column">
              <section className="section-panel section-nested">
                <div className="section-head">
                  <div>
                    <span className="mini-label">
                      <FileText size={14} />
                      当前成果
                    </span>
                    <h2>先看这几张最关键的结果卡</h2>
                  </div>
                  <p>工作区只保留最值得立刻讨论的结构化产物，更多细节拆到成果页和知识库页。</p>
                </div>
                <FeaturedArtifacts
                  projectId={project.id}
                  cards={cards.slice(0, 4)}
                  selectedCardId={selectedCardId}
                  onSelectCard={onSelectCard}
                />
              </section>

              <KnowledgeDigest knowledgeCards={knowledgeCards} />
            </div>

            <DocumentArchiveSection compact documents={generatedDocuments} />
          </div>
        ) : null}

        {activeView === "artifacts" ? (
          <div className="workspace-stack">
            <ArtifactSections
              projectId={project.id}
              cards={cards}
              selectedCardId={selectedCardId}
              onSelectCard={onSelectCard}
            />
            <DocumentArchiveSection documents={generatedDocuments} />
          </div>
        ) : null}

        {activeView === "knowledge" ? (
          <KnowledgeSection
            knowledgeCards={knowledgeCards}
            knowledgeHits={knowledgeHits}
            knowledgeQuery={knowledgeQuery}
            onKnowledgeQueryChange={onKnowledgeQueryChange}
            onSearchKnowledge={onSearchKnowledge}
            pdfUploadLoading={pdfUploadLoading}
            pdfUploadError={pdfUploadError}
            onUploadPdf={onUploadPdf}
          />
        ) : null}

        {activeView === "results" ? (
          <ResultsSummaryPanel projectId={project.id} summary={resultSummary} />
        ) : null}

        {activeView === "roles" ? (
          <RoleExecutionPanel roles={roles} workflowTimeline={workflowTimeline} onRunRole={onRunRole} />
        ) : null}
      </section>
    </section>
  );
}
