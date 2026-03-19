# 引路虾（GuideClaw）技术实施方案

> 本文档用于明确引路虾与 OpenClaw 的关系、系统架构、分阶段实现路径，以及 OpenClaw 的安装与接入时机。

## 一、关系定义

引路虾不是 OpenClaw 的一个简单插件，也不应该直接深度改造 OpenClaw 核心源码。

更准确的关系是：

- 引路虾：独立的科研导航应用
- OpenClaw：引路虾依赖的底层智能运行平台

两者职责分工如下：

| 层级 | 作用 |
| --- | --- |
| 引路虾 | 定义科研场景、工作流、结构化成果、前端体验、项目状态 |
| OpenClaw | 提供 Agent 运行、技能调用、渠道接入、会话记忆、移动端连接 |

一句话概括：

> 引路虾负责“做什么科研工作、怎么推进研究”；OpenClaw 负责“让这些智能能力稳定运行并连接到不同渠道”。

## 二、推荐架构

推荐采用“独立应用 + OpenClaw 集成”的四层架构：

```text
前端工作台
  -> 引路虾 API / BFF
    -> 工作流编排层
      -> 科研 RAG / 文献解析 / 证据回溯
      -> 项目状态与结构化成果存储
      -> OpenClaw Skills / Channels / Agent Runtime
```

### 2.1 架构说明

#### 展示层

- Web 工作台是主界面
- 负责展示研究主题、阶段状态、角色协作过程和结构化成果
- 面向评委和桌面用户

#### 业务层

- 引路虾后端负责项目管理、工作流推进、结构化结果生成
- 是整个产品的核心

#### 智能层

- 科研 RAG 负责文献解析、结构化抽取、证据回溯
- OpenClaw 负责多 Agent、技能调用、飞书等渠道接入

#### 数据层

- 保存项目状态
- 保存文献元数据、向量索引、结构化成果
- 支持连续推进同一个研究项目

## 三、技术选型建议

| 模块 | 建议技术 |
| --- | --- |
| 前端工作台 | Next.js + TypeScript + Tailwind CSS |
| 后端 API | FastAPI |
| 工作流编排 | LangGraph 或自定义状态机 |
| 文献解析 | PyMuPDF |
| 检索与向量库 | PostgreSQL + pgvector |
| 缓存与异步任务 | Redis |
| 文件存储 | 本地磁盘或 MinIO |
| 智能底座 | OpenClaw |
| 移动端入口 | Feishu / Lark via OpenClaw Channel |

## 四、复用优先策略

引路虾不建议从零开始重造基础轮子。比赛阶段的目标是快速完成可演示、可联调、可复用的系统，因此应优先采用成熟开源项目。

### 4.1 推荐优先复用的项目

| 需求 | 推荐复用项目 | 作用 |
| --- | --- | --- |
| 学术 PDF 解析 | `kermitt2/grobid` | 解析论文正文结构、参考文献、元数据 |
| OpenAlex 检索 | `pyalex` | 检索论文、作者、主题、引用关系 |
| 带引用科研问答 | `Future-House/paper-qa` | 为后续证据回溯与 citation-grounded QA 提供能力 |
| Agent / RAG 工作流参考 | `langchain-ai/rag-research-agent-template` | 借用工作流组织思路 |
| Dashboard 骨架 | `next-shadcn-dashboard-starter` 或类似模板 | 快速搭建工作台页面框架 |
| 智能宿主 | `OpenClaw` | Skills、Agent、飞书接入、会话记忆 |

### 4.2 复用原则

- 先复用成熟框架和模板，再做定制化开发
- 不为比赛版重新发明 PDF 解析、文献检索、基础 dashboard、Agent 宿主
- 自研重点只放在：
  - 五个角色的科研工作流
  - 文献卡 / 缺口卡 / 方案卡 / 纪要卡
  - Web 工作台体验
  - OpenClaw 与引路虾后端的接入逻辑

## 五、仓库组织方式

推荐目录结构如下：

```text
openclawapp/
  apps/
    web/                      # 引路虾 Web 工作台
  services/
    api/                      # 引路虾后端 API / 工作流 / RAG
  skills/
    guideclaw-router/
    guideclaw-literature-ra/
    guideclaw-gap-analyst/
    guideclaw-study-designer/
    guideclaw-meeting-secretary/
  openclaw/
    openclaw.env.example
    openclaw-config.md
  docs/
  data/
    samples/
  scripts/
```

### 为什么这样组织

- 引路虾是主产品，代码应独立维护
- OpenClaw 官方源码不建议直接 vendoring 到你的业务仓库
- 你的仓库只保留：
  - 业务代码
  - Skills
  - OpenClaw 配置模板
  - 样例数据

## 六、第一阶段的目标

第一阶段不追求“完整平台”，只追求一个可打穿的比赛 Demo。

唯一主线：

> 机器学习辅助 OLED 材料筛选

唯一闭环：

1. 输入研究方向
2. 上传论文
3. 生成文献卡
4. 生成研究缺口
5. 生成研究方案
6. 生成组会纪要与待办

## 七、第一步现在应该怎么做

第一步不是立刻开发所有功能，也不是先把 OpenClaw 改得很深，而是先把产品骨架定清楚。

### 第一步：初始化项目骨架

当前最先要做的事情：

1. 建立目录结构
2. 建立 Web 工作台和后端服务的空工程
3. 建立 `skills/` 占位目录
4. 明确唯一 Demo 主题为 OLED
5. 定义五个角色的输入输出 schema

这一阶段的目标是：

- 把产品边界定清楚
- 把引路虾与 OpenClaw 的关系定清楚
- 为后续安装和接入 OpenClaw 留好位置

### 第二步：安装 OpenClaw

在项目骨架搭好之后，就应该安装 OpenClaw。

原因：

- 太早安装，容易让整个项目围着 OpenClaw 本身转
- 太晚安装，又会影响 Skills 和渠道接入联调
- 所以最合适的时机是：骨架完成后、业务开发开始前

## 八、OpenClaw 安装策略

### 7.1 安装原则

推荐方式是：

- 安装全局 OpenClaw CLI
- 当前仓库作为业务工作区
- 当前仓库内的 `skills/` 作为工作区技能目录

不推荐方式是：

- 把 OpenClaw 官方源码整体拷贝进当前业务仓库
- 直接在 OpenClaw 核心源码里开发引路虾主逻辑

### 7.2 推荐安装方式

根据 OpenClaw 官方文档，推荐通过官方安装脚本或全局 CLI 安装：

#### 推荐方式 A：官方安装脚本

```bash
curl -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install.sh | bash
```

#### 推荐方式 B：全局安装 CLI

```bash
npm install -g openclaw@latest
```

安装完成后，进行初始化：

```bash
openclaw onboard
```

或：

```bash
openclaw setup
```

常用检查命令：

```bash
openclaw doctor
openclaw status
openclaw dashboard
```

### 7.3 安装后的接入方式

安装完成后，不需要把 OpenClaw 核心代码放进仓库，而是通过以下方式接入：

1. 使用全局 `openclaw` CLI
2. 在当前项目仓库中维护 `skills/`
3. 在 OpenClaw 配置中指向当前工作区
4. 让 Skills 去调用引路虾后端 API

## 九、分阶段实施计划

### 阶段 1：项目骨架与静态工作台

目标：

- 完成项目目录初始化
- 完成 Web 工作台页面骨架
- 完成后端项目骨架
- 定义数据结构和角色 schema

产出：

- `apps/web`
- `services/api`
- `skills/`
- 基础文档与配置模板

### 阶段 2：最小 OLED Demo

目标：

- 用固定样例跑通完整链路
- 先用假数据或半人工数据完成演示

产出：

- 文献卡
- 缺口卡
- 方案卡
- 纪要卡

### 阶段 3：文献解析与结构化抽取

目标：

- 支持上传 PDF
- 解析文献正文
- 生成结构化文献卡
- 支持证据回溯

### 阶段 4：OpenClaw 接入

目标：

- 接入五个角色对应的 Skills
- 接入会话记忆
- 接入 Feishu / 移动端渠道

### 阶段 5：比赛打磨

目标：

- 优化工作台观感
- 优化执行稳定性
- 加缓存和兜底结果
- 打磨 Demo 话术

## 十、比赛版必须具备的功能

### P0：必须有

- 研究项目创建
- PDF 上传
- 文献卡生成
- 缺口卡生成
- 方案卡生成
- 纪要卡生成
- 证据来源展示
- 项目状态保存

### P1：强烈建议有

- 角色执行状态展示
- 一键进入下一阶段
- 飞书端查看摘要与待办
- 结果通知

### P2：有时间再做

- 外部联网文献检索
- 多项目管理
- 导出研究摘要或开题草稿

## 十一、展示方案

### Web 工作台负责展示深度内容

页面建议采用三栏布局：

- 左侧：研究主题、上传论文、当前阶段
- 中间：五个角色的执行状态
- 右侧：文献卡、缺口卡、方案卡、纪要卡

### 飞书负责轻量远程操控

适合放在飞书上的能力：

- 创建项目
- 查看当前进度
- 查看推荐缺口
- 查看待办
- 接收分析完成通知
- 触发进入下一阶段

## 十二、建议的立即执行顺序

如果现在开始做，建议严格按下面顺序推进：

1. 初始化项目骨架
2. 搭建 Web 工作台空页面
3. 搭建后端空服务
4. 写五个角色 schema
5. 安装 OpenClaw CLI
6. 创建 `skills/` 并接通到后端 API
7. 用 OLED 样例跑通第一条完整链路

## 十三、总结

引路虾是主产品，OpenClaw 是底层智能基础设施。

正确的做法不是把引路虾做成一个附属插件，而是把它作为独立的科研导航应用来开发，再通过 Skills、渠道与会话能力接入 OpenClaw。

这样做的结果是：

- Web 端有完整产品形态
- Feishu 端有远程操控能力
- OpenClaw 生态能力被真正利用起来
- 项目结构清晰，后续易扩展、易维护
