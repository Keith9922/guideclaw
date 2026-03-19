import * as Tabs from "@radix-ui/react-tabs";
import { LibraryBig, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { GeneratedDocument, ProjectResearchState, RuntimeHealth } from "@/lib/api";
import { markdownComponents, renderValue, stageMeta } from "./content";
import { TranslatableText } from "./translatable-text";
import type { InsightCard } from "./types";

type DetailSidebarProps = {
  pageLabel: string;
  pageDescription: string;
  projectId?: string;
  projectTitle?: string;
  projectSummary?: string;
  stageLabel?: string;
  stageDescription?: string;
  selectedCard: InsightCard | null;
  summaryContent?: string | null;
  generatedDocuments: GeneratedDocument[];
  runtimeHealth?: RuntimeHealth | null;
  researchState?: ProjectResearchState | null;
  knowledgeCount: number;
  taskCount: number;
};

export function DetailSidebar({
  pageLabel,
  pageDescription,
  projectId,
  projectTitle,
  projectSummary,
  stageLabel,
  stageDescription,
  selectedCard,
  summaryContent,
  generatedDocuments,
  runtimeHealth,
  researchState,
  knowledgeCount,
  taskCount,
}: DetailSidebarProps) {
  const [activeDocumentId, setActiveDocumentId] = useState<string>("");

  useEffect(() => {
    setActiveDocumentId(generatedDocuments[0]?.id ?? "");
  }, [generatedDocuments]);

  const activeDocument = useMemo(
    () => generatedDocuments.find((item) => item.id === activeDocumentId) ?? generatedDocuments[0] ?? null,
    [activeDocumentId, generatedDocuments],
  );

  return (
    <aside className="detail-panel">
      <div className="info-stack detail-info-stack">
        <article className="info-card">
          <span>你现在在看什么</span>
          <strong>{pageLabel}</strong>
          <p>{pageDescription}</p>
        </article>
        <article className="info-card">
          <span>当前课题</span>
          <strong>{projectTitle ?? "尚未选择项目"}</strong>
          <p>{projectSummary ?? "当前没有选中项目，右侧只保留说明信息，不展示任何示例成果。"}</p>
          {stageLabel ? (
            <div className="runtime-badges">
              <span className="badge ghost">{stageLabel}</span>
              <span className="badge ghost">{taskCount} 个任务</span>
              <span className="badge ghost">{knowledgeCount} 条知识源</span>
            </div>
          ) : null}
        </article>
        {researchState ? (
          <details className="detail-disclosure" open>
            <summary>给新人的辅助说明</summary>
            <article className="info-card info-card-embedded">
              <span>系统当前建议你关注</span>
              <strong>{researchState.research_focus || "等待 PI 定义焦点"}</strong>
              <p>{researchState.next_step ?? "当前还没有下一步建议。"}</p>
              {stageLabel ? <p>{stageDescription ?? stageMeta.literature_review.description}</p> : null}
            </article>
          </details>
        ) : null}
        {runtimeHealth ? (
          <details className="detail-disclosure">
            <summary>系统运行方式（演示用，可折叠）</summary>
            <article className="info-card info-card-embedded runtime-info-card">
              <span>OpenClaw 运行方式</span>
              <strong>{runtimeHealth.openclaw.integration_mode === "cli_on_demand" ? "按需 CLI 执行" : runtimeHealth.openclaw.integration_mode}</strong>
              <p>{runtimeHealth.openclaw.call_path}</p>
              <div className="runtime-badges">
                <span className="badge ghost">{runtimeHealth.openclaw.profile}</span>
                <span className="badge ghost">{runtimeHealth.openclaw.agent}</span>
                <span className="badge ghost">
                  {runtimeHealth.openrouter.ready ? "OpenRouter 已就绪" : "OpenRouter 未就绪"}
                </span>
                {runtimeHealth.bohrium ? (
                  <span className="badge ghost">
                    {runtimeHealth.bohrium.ready ? "Bohrium 已配置" : "Bohrium 未就绪"}
                  </span>
                ) : null}
              </div>
            </article>
          </details>
        ) : null}
      </div>

      {projectTitle && selectedCard ? (
        <>
          <div className="panel-head">
            <div>
              <span className="mini-label">
                <Sparkles size={14} />
                详情抽屉
              </span>
              <h2>{selectedCard.title}</h2>
            </div>
          </div>

          <Tabs.Root className="tabs-root detail-tabs" defaultValue="details">
            <Tabs.List className="detail-tab-row">
              <Tabs.Trigger className="detail-tab" value="details">
                结构
              </Tabs.Trigger>
              <Tabs.Trigger className="detail-tab" value="evidence">
                证据
              </Tabs.Trigger>
              <Tabs.Trigger className="detail-tab" value="summary">
                摘要
              </Tabs.Trigger>
            </Tabs.List>

            <Tabs.Content className="detail-content" value="details">
              <div className="detail-summary">
                <TranslatableText
                  as="p"
                  className="detail-summary-text"
                  projectId={projectId}
                  text={selectedCard.summary}
                />
              </div>
              <div className="detail-list">
                {selectedCard.details.map((item) => (
                  <div key={item.label} className="detail-row">
                    <span>{item.label}</span>
                    <strong>{renderValue(item.value)}</strong>
                  </div>
                ))}
              </div>
            </Tabs.Content>

            <Tabs.Content className="detail-content" value="evidence">
              {selectedCard.evidence.length ? (
                <div className="evidence-list">
                  {selectedCard.evidence.map((item, index) => (
                    <article key={`${item.source}-${index}`} className="evidence-card">
                      <strong>
                        {item.source}
                        {item.page
                          ? item.page_to && item.page_to !== item.page
                            ? ` · p.${item.page}-${item.page_to}`
                            : ` · p.${item.page}`
                          : ""}
                      </strong>
                      {item.citation ? <div className="evidence-citation">{item.citation}</div> : null}
                      <TranslatableText
                        as="p"
                        className="evidence-snippet"
                        projectId={projectId}
                        text={item.snippet}
                      />
                      {item.doi || item.url ? (
                        <div className="evidence-links">
                          {item.doi ? <span className="tag-chip">DOI: {item.doi}</span> : null}
                          {item.url ? (
                            <a
                              className="text-link"
                              href={item.url}
                              rel="noreferrer"
                              target="_blank"
                            >
                              打开来源
                            </a>
                          ) : null}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty-state">当前成果卡暂无直接证据片段，可以继续通过角色执行补充。</div>
              )}
            </Tabs.Content>

            <Tabs.Content className="detail-content" value="summary">
              <details className="detail-disclosure" open>
                <summary>研究摘要</summary>
                <div className="summary-block">
                <div className="subhead">
                  <h3>研究摘要</h3>
                  <span>只展示研究结论，不强调底层模型名</span>
                </div>
                <div className="markdown-box markdown-light">
                  <ReactMarkdown components={markdownComponents()} remarkPlugins={[remarkGfm]}>
                    {summaryContent ?? "当前还没有模型摘要，点击工作区上的按钮即可刷新。"}
                  </ReactMarkdown>
                </div>
              </div>
              </details>

              <details className="detail-disclosure">
                <summary>最近生成内容（已存档，可折叠）</summary>
                <div className="summary-block">
                <div className="subhead">
                  <h3>最近生成内容</h3>
                  <span>这些 Markdown 内容已入库，可供后续翻阅</span>
                </div>
                {generatedDocuments.length ? (
                  <>
                    <div className="document-history-list">
                      {generatedDocuments.slice(0, 6).map((item) => (
                        <button
                          key={item.id}
                          className={`document-history-card ${activeDocument?.id === item.id ? "is-active" : ""}`}
                          onClick={() => setActiveDocumentId(item.id)}
                          type="button"
                        >
                        <div className="document-history-head">
                          <strong>{item.title}</strong>
                          <span>{new Date(item.updated_at).toLocaleString("zh-CN")}</span>
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
                          <span className="badge ghost">
                            {item.source === "system"
                              ? "系统沉淀"
                              : item.source === "openclaw"
                                ? "OpenClaw"
                                : "OpenRouter"}
                          </span>
                        </div>
                        <p>{item.content.slice(0, 180)}{item.content.length > 180 ? "..." : ""}</p>
                        </button>
                      ))}
                    </div>

                    {activeDocument ? (
                      <div className="summary-block summary-block-nested">
                        <div className="subhead">
                          <h3>{activeDocument.title}</h3>
                          <span>
                            {activeDocument.source === "system"
                              ? "系统自动沉淀"
                              : activeDocument.source === "openclaw"
                                ? "OpenClaw 角色执行记录"
                                : "模型生成摘要"}
                          </span>
                        </div>
                        <div className="markdown-box markdown-light markdown-tall">
                          <ReactMarkdown components={markdownComponents()} remarkPlugins={[remarkGfm]}>
                            {activeDocument.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <div className="empty-state">当前项目还没有持久化的 Markdown 内容。</div>
                )}
              </div>
              </details>
            </Tabs.Content>
          </Tabs.Root>
        </>
      ) : (
        <div className="empty-state">
          <strong>{projectTitle ? "等待你选择成果卡" : "辅助区当前保持空白"}</strong>
          <p>
            {projectTitle
              ? "当你在中间页面选中一张成果卡后，这里才会出现对应的结构、证据和摘要。"
              : "先在项目管理页创建真实课题，再进入工作区、成果页或角色页。"}
          </p>
          {knowledgeCount ? (
            <div className="detail-side-note">
              <span className="mini-label">
                <LibraryBig size={14} />
                当前知识库
              </span>
              <p>当前项目已经有 {knowledgeCount} 条知识源，可以去知识库页继续查链接和来源。</p>
            </div>
          ) : null}
        </div>
      )}
    </aside>
  );
}
