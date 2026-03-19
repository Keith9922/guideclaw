export type RoleStatus = {
  name: string;
  title: string;
  state: "在线" | "进行中" | "待确认" | "阻塞";
  note: string;
  progress: number;
};

export type ResultCard = {
  title: string;
  summary: string;
  tags: string[];
  updatedAt: string;
};

export const project = {
  name: "引路虾研究工作台",
  code: "GLX-WB-001",
  stage: "文献梳理 -> 缺口发现 -> 方案生成 -> 纪要沉淀",
  summary:
    "面向科研新人的本地 mock 工作台，用来快速看清项目状态、角色分工和阶段性成果。",
  owner: "引路虾项目组",
  lastSync: "2026-03-18 09:20"
};

export const roleStatuses: RoleStatus[] = [
  {
    name: "文献侦察员",
    title: "扫描近三个月综述与核心论文",
    state: "在线",
    note: "已更新 12 篇候选文献，优先级按引用链排序。",
    progress: 84
  },
  {
    name: "研究缺口分析员",
    title: "提炼共性结论与空白点",
    state: "进行中",
    note: "正在对比 4 组实验结论，缺口假设已写入草稿。",
    progress: 63
  },
  {
    name: "方案编排员",
    title: "把缺口收敛为可执行研究方案",
    state: "待确认",
    note: "需要确认样本量与实验窗口，再输出方案版本 0.2。",
    progress: 41
  },
  {
    name: "实验协调员",
    title: "同步实验计划与资源排期",
    state: "阻塞",
    note: "等待设备时段确认，当前排期卡在周四下午。",
    progress: 28
  },
  {
    name: "纪要归档员",
    title: "整理组会纪要与行动项",
    state: "在线",
    note: "本周纪要模板已生成，可直接挂到成果卡。",
    progress: 91
  }
];

export const resultCards: ResultCard[] = [
  {
    title: "文献综述卡",
    summary: "总结当前主题的研究脉络，附带引用来源与可追踪标签。",
    tags: ["综述", "引用链", "待补充"],
    updatedAt: "10 分钟前"
  },
  {
    title: "研究缺口卡",
    summary: "把重复结论、空白区域和争议点汇总成可讨论条目。",
    tags: ["缺口", "争议点", "优先级高"],
    updatedAt: "35 分钟前"
  },
  {
    title: "方案草稿卡",
    summary: "包含假设、变量、实验步骤和需要补齐的前置条件。",
    tags: ["方案", "实验设计", "待确认"],
    updatedAt: "1 小时前"
  },
  {
    title: "组会纪要卡",
    summary: "记录讨论结论、责任人和下一步动作，方便后续追踪。",
    tags: ["纪要", "行动项", "待分发"],
    updatedAt: "今天"
  }
];

export const resultTags = [
  "文献综述",
  "研究缺口",
  "实验方案",
  "组会纪要",
  "行动项",
  "引用链",
  "待确认",
  "优先级高",
  "本地 mock"
];

export const mockWorkbenchData = {
  project,
  roleStatuses,
  resultCards,
  resultTags,
};
