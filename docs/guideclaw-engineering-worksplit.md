# 引路虾（GuideClaw）工程拆分与并行开发方案

> 目标：在不重复造轮子的前提下，快速搭出“引路虾”比赛版最小可用系统，并支持多 IDE 并行开发。

## 一、最终定版方案

### 1.1 产品定位

引路虾是一个面向科研新人的研究导航应用，负责把一个模糊研究方向推进成一版可讨论的研究方案。

它不是 OpenClaw 插件本体，也不是 OpenClaw 的 UI 壳，而是：

- 独立的 Web 工作台
- 独立的业务后端
- 独立的科研工作流
- 通过 Skills 和渠道能力接入 OpenClaw

### 1.2 与 OpenClaw 的关系

- 引路虾负责：
  - 科研场景定义
  - 工作流编排
  - 文献卡 / 缺口卡 / 方案卡 / 纪要卡
  - Web 工作台
  - 项目状态持久化
- OpenClaw 负责：
  - Agent 运行
  - Skills 调用
  - 会话记忆
  - 飞书 / 移动端接入

### 1.3 核心架构

```text
Web 工作台
  -> 引路虾 API
    -> 工作流编排层
      -> 文献解析 / 结构化抽取 / 证据回溯
      -> 项目状态存储
      -> OpenClaw Skills / 渠道路由
```

### 1.4 复用优先策略

这套系统不从零造轮子，优先复用成熟开源项目。

| 需求 | 推荐复用项目 | 用法 |
| --- | --- | --- |
| 学术 PDF 解析 | `kermitt2/grobid` | 解析论文结构、参考文献、正文 |
| 学术元数据检索 | `pyalex` | 检索论文、作者、主题、相关推荐 |
| 带引用科研问答 | `Future-House/paper-qa` | 做带证据回答和文献 grounding |
| Agent 工作流参考 | `langchain-ai/rag-research-agent-template` | 借工作流结构，不直接照搬 |
| Dashboard 前端骨架 | `next-shadcn-dashboard-starter` | 快速搭工作台 UI |
| 智能宿主与渠道 | `OpenClaw` | Skills、Agent、飞书接入、记忆 |

### 1.5 工程执行原则

- 前端优先复用现成 dashboard 模板，不自己从零写布局系统
- 后端优先参考现成 research / RAG agent 模板，不自己重写工作流组织方式
- 文献解析优先接 GROBID / PyMuPDF / PaperQA / PyAlex，不自己重写底层解析器
- OpenClaw 接入优先走官方 CLI + 工作区 skills，不改核心源码

### 1.6 比赛版必须打穿的唯一主线

唯一主线：

> 机器学习辅助 OLED 材料筛选

唯一闭环：

1. 输入研究方向
2. 上传论文
3. 生成文献卡
4. 生成研究缺口
5. 生成研究方案
6. 生成组会纪要与待办

## 二、工程模块拆分

为了支持并行开发，整个工程拆成 5 个相对独立的模块。

### 模块 A：前端工作台

负责：

- Web 端页面骨架
- 三栏布局
- 角色状态展示
- 文献卡 / 缺口卡 / 方案卡 / 纪要卡展示
- 证据抽屉

目录建议：

```text
apps/web/
```

### 模块 B：业务后端

负责：

- 项目管理 API
- 工作流推进 API
- Artifact 聚合输出
- 项目状态持久化

目录建议：

```text
services/api/
```

### 模块 C：科研解析与 RAG

负责：

- PDF 解析
- GROBID 接入
- 文献 chunk 构建
- 结构化文献卡生成
- 证据回溯

目录建议：

```text
services/api/src/rag/
services/api/src/parsers/
services/api/src/evidence/
```

### 模块 D：OpenClaw Skills / 渠道接入

负责：

- 五个角色的 skills
- Skills 调用后端 API
- 未来的飞书消息入口

目录建议：

```text
skills/
openclaw/
```

### 模块 E：样例数据与文档

负责：

- OLED 样例数据
- Demo 样例论文
- 提交文案
- 架构图、说明文档

目录建议：

```text
data/samples/
docs/
```

## 三、推荐的并行分工

建议同时开 4 个 IDE。

原因：

- 4 个工作包已经足够并行
- 再多会出现强依赖和相互阻塞
- 文档与样例数据可以穿插完成，不一定单独占一个 IDE

---

## 四、IDE 分工方案

## IDE 1：前端工作台

### 负责范围

- `apps/web/**`

### 不要修改

- `services/**`
- `skills/**`
- `docs/**`

### 目标

先搭出一个可演示的研究工作台壳子，不接真实后端也可以先用 mock 数据。

### 必做功能

1. 三栏布局
2. 项目头部信息区
3. 五角色状态卡
4. 右侧成果标签页
5. 文献卡、缺口卡、方案卡、纪要卡组件
6. 证据抽屉 UI

### 技术要求

- 基于 `Next.js + TypeScript`
- 优先复用 dashboard starter，不要自己手写整套布局
- 先全部用 mock JSON 驱动

### 交付标准

- 打开页面就能看到一个完整工作台
- 切换成果卡不卡壳
- OLED 的假数据可完整展示

---

## IDE 2：后端 API 与工作流

### 负责范围

- `services/api/**`

### 不要修改

- `apps/web/**`
- `skills/**`

### 目标

先把项目对象、artifact 对象和阶段工作流定下来。

### 必做功能

1. `POST /projects`
2. `POST /projects/{id}/papers`
3. `POST /projects/{id}/run`
4. `GET /projects/{id}`
5. `GET /projects/{id}/artifacts`
6. `GET /projects/{id}/evidence`

### 工作流阶段

```text
project_init
-> literature_review
-> gap_analysis
-> study_design
-> meeting_summary
```

### 数据模型

至少先定义：

- `Project`
- `Paper`
- `LiteratureCard`
- `GapCard`
- `PlanCard`
- `MeetingNote`
- `WorkflowRun`

### 技术要求

- `FastAPI`
- 先允许内存存储或 sqlite 起步
- 工作流组织方式优先参考 research / RAG agent 模板
- 接口先稳定，再切 PostgreSQL

### 交付标准

- 能返回一套完整 mock artifact
- 前端可以稳定调用

---

## IDE 3：科研 RAG / 文献处理

### 负责范围

- `services/api/src/rag/**`
- `services/api/src/parsers/**`
- `services/api/src/evidence/**`
- `data/samples/**`

### 不要修改

- `apps/web/**`
- `skills/**`

### 目标

优先接入论文解析和证据提取，不要求一开始就做最强检索。

### 必做功能

1. PDF 上传后的文本抽取
2. 结构化文献卡生成
3. 证据片段定位
4. OLED 样例论文的解析样例

### 推荐复用

- `GROBID`
- `PyMuPDF`
- `paper-qa`
- `pyalex`

### 技术要求

- 先用本地 3 到 5 篇样例论文打穿
- 输出统一 schema
- 每个结论至少返回一条 evidence

### 交付标准

- 对指定样例论文，能输出：
  - 研究问题
  - 方法
  - 数据
  - 结果
  - 局限
  - 证据片段

---

## IDE 4：OpenClaw / Skills / 移动端入口

### 负责范围

- `skills/**`
- `openclaw/**`
- 启动脚本与配置说明

### 不要修改

- `apps/web/**`
- `services/api/**`

### 目标

把 OpenClaw 接进来，但不侵入业务代码。

### 必做功能

1. 安装 OpenClaw CLI
2. 配置当前项目工作区
3. 建立五个角色技能目录
4. 每个 skill 能调后端 API
5. 预留 Feishu 接入位

### 五个技能目录

```text
skills/
  guideclaw-router/
  guideclaw-literature-ra/
  guideclaw-gap-analyst/
  guideclaw-study-designer/
  guideclaw-meeting-secretary/
```

### 技术要求

- 不拉 OpenClaw 源码进业务仓库
- 只安装 CLI
- 只维护配置模板和 skills
- 复用官方推荐的工作区 skills 接入方式

### 交付标准

- 本地 OpenClaw 能识别当前仓库下的 skills
- 能通过一个 skill 调后端接口拿到结果

---

## 五、统一约束

为了避免多 IDE 互相打架，统一遵循以下规则：

### 5.1 目录边界

- IDE 1 只动 `apps/web`
- IDE 2 只动 `services/api`
- IDE 3 只动 `services/api/src/rag`、`parsers`、`evidence`、`data/samples`
- IDE 4 只动 `skills`、`openclaw`

### 5.2 接口约束

后端统一先返回 mock 或静态 schema，不等真实模型接通再联调。

### 5.3 数据契约优先

前后端先对齐以下 schema，再开始各自实现：

- `Project`
- `LiteratureCard`
- `GapCard`
- `PlanCard`
- `MeetingNote`

### 5.4 不要做的事

- 不要一开始接太多真实外部服务
- 不要一开始支持多个研究方向
- 不要一开始做飞书全功能
- 不要修改 OpenClaw 核心源码

## 六、建议的开发顺序

### 第 1 天

- 建仓库结构
- 搭前端骨架
- 搭后端骨架
- 定 schema

### 第 2 天

- 前端接 mock 数据
- 后端出 mock API
- RAG 组准备 OLED 样例论文
- OpenClaw 组安装 CLI 并建 skills 占位

### 第 3 到 4 天

- 接 PDF 解析
- 接文献卡
- 接缺口卡和方案卡
- 前端接真接口

### 第 5 到 6 天

- 接证据回溯
- 接组会纪要
- 接 OpenClaw skill -> API 通路

### 第 7 天

- 打磨演示
- 补缓存和兜底
- 准备比赛 Demo

## 七、第一步现在就该做什么

现在立刻做的第一步只有一个：

> 初始化项目骨架，并锁定并行开发边界。

具体动作：

1. 建 `apps/web`
2. 建 `services/api`
3. 建 `skills`
4. 建 `openclaw`
5. 建 `data/samples`
6. 写统一 schema 草案

在这一步做完之前，不建议任何 IDE 自由开发业务逻辑。

## 八、OpenClaw 什么时候安装

结论：

> 项目骨架建好后立刻安装。

时机就是：

- 在目录结构建好之后
- 在 skills 开始真正编写之前
- 在飞书接入之前

### 推荐安装命令

```bash
curl -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install.sh | bash
```

或：

```bash
npm install -g openclaw@latest
```

安装后执行：

```bash
openclaw onboard
openclaw doctor
```

## 九、最终执行建议

这套方案最适合的执行方式是：

- 先开 4 个 IDE
- 先按目录边界拆任务
- 先跑通 OLED 主线
- 再逐步把 OpenClaw、飞书和 RAG 做实

一句话总结：

> 用现成轮子搭底座，用引路虾定义产品，用 OpenClaw 提供智能基础设施，用多 IDE 并行把比赛版快速做出来。
