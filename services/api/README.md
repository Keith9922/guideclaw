# 引路虾 API

引路虾的 FastAPI 后端。当前项目池默认为空，只有用户创建真实课题后才会产生项目数据。项目、成果卡和工作流轨迹现在会持久化到 SQLite，不再因为服务重启而丢失。

## 运行

在 `services/api` 目录下执行：

```bash
cp .env.example .env.local
pip install -e .
uvicorn app.main:app --reload
```

## 接口

- `GET /projects`
- `POST /projects`
- `DELETE /projects/{id}`
- `GET /projects/{id}`
- `GET /projects/{id}/artifacts`
- `GET /projects/{id}/workflow`
- `GET /projects/{id}/knowledge-sources`
- `POST /projects/{id}/investigate`
- `POST /projects/{id}/llm-summary`
- `POST /projects/{id}/agent-run`
- `GET /projects/{id}/agent-run/stream`
- `GET /health`

`.env.local` 中预留了以下配置：

- `MINIMAX_API_KEY`
- `MINIMAX_MODEL`
- `GUIDECLAW_ALLOWED_ORIGINS`
- `GUIDECLAW_API_BASE_URL`
- `GUIDECLAW_DATABASE_PATH`
- `GUIDECLAW_OPENCLAW_BINARY`
- `GUIDECLAW_OPENCLAW_PROFILE`
- `GUIDECLAW_OPENCLAW_AGENT`

## 当前 OpenClaw 集成方式

当前不是“FastAPI 调 OpenClaw HTTP 服务”，而是下面这条链路：

```text
Web 工作台 -> FastAPI -> openclaw CLI (--local --json) -> 返回结构化结果 / SSE 流
```

这意味着：

- `FastAPI` 是常驻后端
- `OpenClaw` 当前以按需 CLI 执行层参与
- 角色页和工作区里的执行动作，都会通过 `/projects/{id}/agent-run` 或 `/projects/{id}/agent-run/stream` 触发 OpenClaw
- 现在还不是飞书/移动端那种常驻通道服务形态
- workspace skills 依赖 `GUIDECLAW_API_BASE_URL`；环境变量注入后，`openclaw --profile guideclaw skills list` 才会稳定显示 `ready`

你可以通过 `GET /health` 查看当前运行模式和 OpenClaw 接入信息。

## 数据持久化

当前默认使用 SQLite：

```text
GUIDECLAW_DATABASE_PATH=/Users/ronggang/code/funcode/openclawapp/data/guideclaw.db
```

持久化内容包括：

- 研究项目元数据
- 文献卡、缺口卡、方案卡、纪要卡
- 多 Agent 协作步骤轨迹
- 项目级知识库候选源（当前以 OpenAlex 论文源为主）

## 证据层现状

当前证据层已经从“纯模型摘要”升级为“OpenAlex grounded”的结构化证据：

- 每条文献证据都尽量绑定到真实候选论文
- 会保留 `source / citation / DOI / url / snippet`
- `snippet` 优先来自 OpenAlex 摘要或元数据，而不是模型自由改写

下一阶段再接：

- PDF 上传
- GROBID 结构化解析
- PaperQA / 引文级证据回溯
