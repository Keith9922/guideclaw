# OpenClaw 安装与接入说明

## 接入原则

- 只使用全局 `openclaw` CLI
- 当前仓库只维护 workspace skills 和配置模板
- 不把 OpenClaw 官方源码 vendoring 到仓库
- 不修改系统全局 OpenClaw 配置

## 推荐安装方式

优先按 OpenClaw 官方方式安装全局 CLI，例如：

```bash
npm install -g openclaw@latest
```

安装后先做基础检查：

```bash
openclaw --version
openclaw doctor
```

## 本仓库中的接入方式

当前仓库里的真实调用链路是：

```text
Web 工作台 -> 引路虾 FastAPI -> openclaw CLI (--local --json) -> 角色输出
```

也就是说：

1. Web 工作台只调用引路虾后端
2. 引路虾后端按需拉起 `openclaw` CLI
3. OpenClaw 使用 `guideclaw` profile 和 `main` agent 执行一轮角色任务
4. 返回结果后，由后端再通过普通 JSON 或 SSE 流式回传给前端

这不是一个“OpenClaw 常驻 HTTP 服务”方案，而是一个“OpenClaw 按需执行层”方案。

## 配置落点

你需要在自己的本地环境或 OpenClaw CLI 侧完成以下映射：

- workspace 根目录 -> `WORKSPACE_ROOT`
- skills 目录 -> `WORKSPACE_ROOT/skills`
- 引路虾后端地址 -> `GUIDECLAW_API_BASE_URL`
- OpenRouter 模型配置 -> `OPENROUTER_BASE_URL`、`OPENROUTER_API_KEY`、`OPENROUTER_MODEL`
- Bohrium 文献技能配置 -> `BOHRIUM_ACCESS_KEY` / `ACCESS_KEY`
- 文献解析与问答后端 -> `GROBID_BASE_URL`、`PYALEX_API_BASE_URL`、`PAPERQA_SERVICE_URL`

模板文件见：

- `openclaw/openclaw.config.template.yml`
- `openclaw/openclaw.env.example`

## 当前已起作用的部分

- `OpenClaw CLI`：由 FastAPI 真实调用
- `guideclaw` profile：由后端命令行参数指定
- `main agent`：由后端命令行参数指定
- `OpenRouter`：通过环境变量注入到 OpenClaw 本地执行环境
- `agent-run/stream`：FastAPI 侧把 OpenClaw 的结果包装成 SSE，供前端流式展示
- `Bohrium skills`：已安装到工作区，但只有在 `ACCESS_KEY` 或 `BOHRIUM_ACCESS_KEY` 配置后才会真正可调用

## 当前还没有完全收口的部分

- 当前集成模式仍然是 `cli_on_demand`，不是常驻 OpenClaw 通道服务
- workspace skills 依赖 `GUIDECLAW_API_BASE_URL` 环境变量；裸跑时可能显示 `missing`，带上后端地址后会变成 `ready`
- 还没有升级成飞书/移动端可复用的常驻通道层
- session 隔离链路已经接入，但仍应持续验证不同项目之间的记忆隔离表现

## 外部轮子的复用方式

OpenClaw skills 不直接实现复杂能力，只负责把任务交给引路虾后端。

推荐分工如下：

- `guideclaw-literature-assistant` -> 优先使用 `bohrium-paper-search` / `bohrium-pdf-parser` / `bohrium-knowledge-base` / `web-search`，并回读引路虾后端中的知识库与文献卡
- `guideclaw-gap-analyst` -> 调引路虾后端的缺口分析接口
- `guideclaw-study-designer` -> 调引路虾后端的方案生成接口；若任务是论文复现，再使用 `proposal-agent`
- `guideclaw-meeting-secretary` -> 调引路虾后端的纪要沉淀接口
- `guideclaw-principal-investigator` -> 调引路虾后端的阶段判断和任务拆分接口

## 典型接入流程

```bash
# 1. 安装全局 CLI
npm install -g openclaw@latest

# 2. 检查当前工作区
./scripts/check-openclaw-env.sh

# 3. 在你自己的本地环境里，把 workspace root 指向本仓库
# 4. 让 OpenClaw 读取本仓库的 skills 目录
# 5. 让 skills 调用引路虾后端，而不是直接做底层解析
```
