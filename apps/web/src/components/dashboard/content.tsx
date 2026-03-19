"use client";

import type { ComponentProps } from "react";
import {
  Atom,
  Bot,
  BrainCircuit,
  FileSearch,
  FileText,
  FlaskConical,
  FolderKanban,
  Lightbulb,
  LibraryBig,
  NotebookPen,
  SearchCheck,
  Sparkles,
} from "lucide-react";
import type {
  AgentTask,
  ApiKnowledgeSource,
  ProjectResearchState,
  WorkbenchData,
  WorkflowStep,
} from "@/lib/api";
import type {
  AgentBoardTask,
  DashboardView,
  EmptyViewMeta,
  InsightCard,
  InsightCategory,
  KnowledgeCard,
  ProjectPulse,
  RoleCard,
  ViewMeta,
  WorkflowTimelineItem,
} from "./types";

export const stageMeta: Record<string, { label: string; description: string }> = {
  literature_review: {
    label: "文献梳理",
    description: "先把领域地图、代表论文和可引用的证据搭起来。",
  },
  gap_analysis: {
    label: "缺口判断",
    description: "从已有工作中筛出真正值得推进的优先问题。",
  },
  proposal: {
    label: "方案成形",
    description: "把优先缺口收成能直接讨论的一版研究方案。",
  },
  meeting_notes: {
    label: "纪要沉淀",
    description: "把结论、分工和下一步推进顺序固化下来。",
  },
};

export const categoryLabels: Record<InsightCategory, string> = {
  all: "全部成果",
  literature: "文献卡",
  gap: "缺口卡",
  plan: "方案卡",
  meeting: "纪要卡",
};

export const roleNameMap: Record<AgentBoardTask["role"], string> = {
  principal_investigator: "课题负责人",
  literature_assistant: "文献助理",
  gap_analyst: "选题分析员",
  study_designer: "方案设计师",
  meeting_secretary: "组会秘书",
};

const roleIconMap = {
  principal_investigator: BrainCircuit,
  literature_assistant: SearchCheck,
  gap_analyst: Lightbulb,
  study_designer: FlaskConical,
  meeting_secretary: NotebookPen,
};

export const viewLabels: Record<DashboardView, ViewMeta> = {
  workspace: {
    label: "工作区",
    title: "研究主舞台",
    description: "把 PI 编排、Agent 分发、证据来源和核心成果放在同一张主舞台里。",
    icon: Sparkles,
  },
  artifacts: {
    label: "成果",
    title: "结构化成果",
    description: "把文献卡、缺口卡、方案卡和纪要卡拆开查看，方便汇报与复用。",
    icon: FileText,
  },
  knowledge: {
    label: "知识库",
    title: "项目知识库",
    description: "查看候选论文、原始链接和知识检索结果，避免回答跑偏。",
    icon: LibraryBig,
  },
  results: {
    label: "结果汇总",
    title: "最终交付物",
    description: "把当前课题最有价值的结果收成一份适合科研新人直接阅读和使用的交付页。",
    icon: FileText,
  },
  roles: {
    label: "角色",
    title: "角色执行",
    description: "单独触发 OpenClaw 角色，让每个 Agent 在真实项目上下文中执行。",
    icon: Bot,
  },
  projects: {
    label: "项目",
    title: "项目管理",
    description: "一切从真实课题开始。先建项目，再进入工作区推进研究。",
    icon: FolderKanban,
  },
};

export const emptyViewCopy: Record<DashboardView, EmptyViewMeta> = {
  workspace: {
    title: "还没有激活的研究项目",
    description: "先创建真实课题，再让 PI 启动这轮研究编排。工作区不会再预置假数据。",
    actionLabel: "去创建研究项目",
  },
  artifacts: {
    title: "还没有成果卡",
    description: "只有在真实项目完成首轮调查后，成果页才会出现文献卡、缺口卡、方案卡和纪要卡。",
    actionLabel: "先创建并调查项目",
  },
  knowledge: {
    title: "当前知识库为空",
    description: "知识库由真实检索结果驱动。请先创建课题并运行首轮调查，再来看引用源和知识搜索。",
    actionLabel: "先创建并调查项目",
  },
  results: {
    title: "当前还没有结果汇总",
    description: "结果汇总依赖真实项目、知识库和成果卡。请先创建课题并完成首轮调查。",
    actionLabel: "先创建并调查项目",
  },
  roles: {
    title: "当前没有可执行上下文",
    description: "角色执行依赖当前项目、研究状态和知识库。没有项目时这里只保持空白。",
    actionLabel: "先创建研究项目",
  },
  projects: {
    title: "项目池当前为空",
    description: "输入一个真实课题和说明，系统才会围绕它建立编排、知识库和成果沉淀。",
    actionLabel: "立即创建课题",
  },
};

export function markdownComponents() {
  return {
    h2: (props: ComponentProps<"h2">) => <h2 className="md-h2" {...props} />,
    h3: (props: ComponentProps<"h3">) => <h3 className="md-h3" {...props} />,
    p: (props: ComponentProps<"p">) => <p className="md-p" {...props} />,
    ul: (props: ComponentProps<"ul">) => <ul className="md-ul" {...props} />,
    ol: (props: ComponentProps<"ol">) => <ol className="md-ol" {...props} />,
    li: (props: ComponentProps<"li">) => <li className="md-li" {...props} />,
    table: (props: ComponentProps<"table">) => <table className="md-table" {...props} />,
    th: (props: ComponentProps<"th">) => <th className="md-th" {...props} />,
    td: (props: ComponentProps<"td">) => <td className="md-td" {...props} />,
    hr: () => <hr className="md-hr" />,
    code: (props: ComponentProps<"code">) => <code className="md-code" {...props} />,
  };
}

export function renderValue(value: string | string[]) {
  return Array.isArray(value) ? value.join("、") : value;
}

export function formatDuration(durationMs: number | null | undefined) {
  if (!durationMs) return "未记录";
  if (durationMs < 1000) return `${durationMs} ms`;
  return `${(durationMs / 1000).toFixed(1)} s`;
}

export function getStageLabel(stage: string) {
  return stageMeta[stage]?.label ?? stage;
}

function sourceTypeLabel(sourceType: ApiKnowledgeSource["source_type"]) {
  switch (sourceType) {
    case "bohrium_paper_search":
      return "Bohrium 论文检索";
    case "pdf_upload":
      return "PDF 上传";
    case "manual":
      return "手工录入";
    case "skill_ingest":
      return "Skill 导入";
    default:
      return "OpenAlex / 回退";
  }
}

export function buildProjectPulse(workbench: WorkbenchData | null): ProjectPulse | null {
  if (!workbench) {
    return null;
  }
  const state = workbench.research_state;
  return {
    focus: state.research_focus || workbench.project.title,
    whyNow: state.why_now || "当前还没有写入更具体的研究背景。",
    nextStep: state.next_step || "先启动首轮调查，产出文献卡和缺口卡。",
    provider: state.provider_note || "当前还没有外部检索来源。",
    recommendedGap: state.recommended_gap_title || "等待选题分析员收敛优先缺口。",
  };
}

export function buildKnowledgeCards(sources: ApiKnowledgeSource[] = []): KnowledgeCard[] {
  return sources.map((source) => ({
    ...source,
    label: sourceTypeLabel(source.source_type),
  }));
}

export function buildInsightCards(workbench: WorkbenchData | null): InsightCard[] {
  if (!workbench) {
    return [];
  }

  return [
    ...workbench.artifacts.literature_cards.map((card) => ({
      id: card.id,
      category: "literature" as const,
      title: card.title,
      summary: `${card.research_question}｜${card.key_result}`,
      status: `${card.evidence.length} 条证据`,
      tags: ["文献卡", card.method, card.data_source],
      details: [
        { label: "研究问题", value: card.research_question },
        { label: "方法", value: card.method },
        { label: "数据来源", value: card.data_source },
        { label: "核心结果", value: card.key_result },
        { label: "局限", value: card.limitations },
      ],
      evidence: card.evidence,
    })),
    ...workbench.artifacts.gap_cards.map((card) => ({
      id: card.id,
      category: "gap" as const,
      title: card.title,
      summary: card.why_it_matters,
      status: `重要性 ${card.importance_score}/10`,
      tags: ["缺口卡", card.gap_type, `可行性 ${card.feasibility_score}/10`],
      details: [
        { label: "缺口类型", value: card.gap_type },
        { label: "为什么重要", value: card.why_it_matters },
        {
          label: "综合评分",
          value: [
            `新颖性 ${card.novelty_score}/10`,
            `重要性 ${card.importance_score}/10`,
            `可行性 ${card.feasibility_score}/10`,
          ],
        },
      ],
      evidence: card.evidence,
    })),
    ...workbench.artifacts.plan_cards.map((card) => ({
      id: card.id,
      category: "plan" as const,
      title: "首轮研究方案",
      summary: `${card.research_question}｜验证：${card.validation}`,
      status: `${card.methods.length} 条方法路线`,
      tags: ["方案卡", ...card.metrics],
      details: [
        { label: "研究问题", value: card.research_question },
        { label: "边界", value: card.boundary },
        { label: "数据来源", value: card.data_source },
        { label: "指标", value: card.metrics },
        { label: "方法", value: card.methods },
        { label: "验证", value: card.validation },
      ],
      evidence: card.evidence,
    })),
    ...workbench.artifacts.meeting_notes.map((card) => ({
      id: card.id,
      category: "meeting" as const,
      title: "本轮纪要与行动项",
      summary: `${card.decisions.join("；")}｜下一步：${card.next_step}`,
      status: `${card.todos.length} 个待办`,
      tags: ["纪要卡", ...card.todos.slice(0, 2)],
      details: [
        { label: "结论", value: card.decisions },
        { label: "未解决问题", value: card.open_questions },
        { label: "待办", value: card.todos },
        { label: "下一步", value: card.next_step },
      ],
      evidence: card.evidence,
    })),
  ];
}

export function buildRoleCards(
  state: ProjectResearchState | undefined,
  workflowSteps: WorkflowStep[] = [],
  tasks: AgentTask[] = [],
): RoleCard[] {
  const byRole = new Map(tasks.map((task) => [task.role, task]));
  return (Object.keys(roleNameMap) as Array<keyof typeof roleNameMap>).map((role) => {
    const task = byRole.get(role);
    const workflowMatch = workflowSteps.find((step) => step.role === role);
    const stage = workflowMatch ? workflowMatch.role : "literature_review";
    let roleState: RoleCard["state"] = "待命";
    if (task?.status === "completed") roleState = "已完成";
    if (task?.status === "running") roleState = "执行中";
    if (task?.status === "blocked") roleState = "待命";
      return {
        id: role,
        skill: `guideclaw-${role.replace(/_/g, "-")}`,
        name: roleNameMap[role],
      title: task?.title ?? roleNameMap[role],
      description: task?.objective ?? state?.research_focus ?? "等待项目上下文。",
      stage,
      state: roleState,
      progress: task?.status === "completed" ? 100 : task?.status === "running" ? 60 : 0,
      outputSummary: task?.output_summary ?? workflowMatch?.summary,
      workflowIndex: workflowMatch ? workflowSteps.indexOf(workflowMatch) + 1 : undefined,
      source: task ? "workflow" : "stage",
    };
  });
}

export function buildAgentBoardTasks(tasks: AgentTask[] = []): AgentBoardTask[] {
  return tasks.map((task) => ({
    ...task,
    roleName: roleNameMap[task.role],
    isPrimary: task.role === "principal_investigator",
  }));
}

export function buildWorkflowTimeline(workflowSteps: WorkflowStep[] = []): WorkflowTimelineItem[] {
  return workflowSteps.map((step, index) => ({
    ...step,
    index: index + 1,
    roleName: roleNameMap[step.role] ?? step.role,
    handoffLabel:
      index === 0
        ? "由课题标题和说明触发"
        : `承接上一步：${roleNameMap[workflowSteps[index - 1]?.role] ?? workflowSteps[index - 1]?.role}`,
  }));
}

export function getRoleIcon(role: AgentTask["role"] | RoleCard["id"]) {
  return roleIconMap[role] ?? Atom;
}

export function getKnowledgeMeta(sources: ApiKnowledgeSource[]) {
  const withLinks = sources.filter((item) => Boolean(item.url || item.doi)).length;
  const withAbstract = sources.filter((item) => Boolean(item.abstract)).length;
  return {
    total: sources.length,
    withLinks,
    withAbstract,
  };
}

export const projectEntryHighlights = [
  {
    title: "一条课题，一条工作流",
    description: "项目是根对象。PI 编排、知识库、成果卡、角色执行都围绕同一个项目 ID 展开。",
    icon: FolderKanban,
  },
  {
    title: "证据优先，不靠脑补",
    description: "文献来源会优先带 DOI、引用和原始链接。后续接 PDF/RAG 时也沿着这个中轴继续收紧。",
    icon: FileSearch,
  },
  {
    title: "先收敛，再放大",
    description: "先让 PI 定焦，再让文献助理补证、选题分析员筛缺口、方案设计师出首轮方案。",
    icon: BrainCircuit,
  },
];
