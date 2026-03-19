---
name: web-search
description: "Search the web via Google (searchapi.io) through Bohrium gateway. Use when: user needs real-time web info, news, tech docs, fact-checking, or references with links. NOT for: academic paper search, internal knowledge base, or file/dataset operations."
metadata: {
  "openclaw": {
    "primaryEnv": "ACCESS_KEY"
  }
}
---

# SKILL: 网页搜索

## 概述

通过 **Google 搜索引擎** 进行网页搜索，由 searchapi.io 提供支持，经 Bohrium 网关鉴权与限流。请求使用固定网关密钥，**无需计费**，但需在 `openclaw.json` 中配置 `ACCESS_KEY` 并通过鉴权。

**接口概要**

| 项目 | 说明 |
|------|------|
| **Path** | `/openapi/v1/search/web` |
| **Method** | GET |
| **Auth** | 请求头携带 `accessKey`（来自 `env.ACCESS_KEY`） |
| **Rate Limit** | 继承全局 v1 限流 |

**适用场景：** 实时信息与新闻、技术文档与教程、事实核查与资料补充。

**无 CLI 支持** — 通过 HTTP GET 调用。

---

## 认证配置

ACCESS_KEY 从 OpenClaw 配置文件 `~/.openclaw/openclaw.json` 中读取：

```json
"web-search": {
  "enabled": true,
  "apiKey": "YOUR_ACCESS_KEY",
  "env": {
    "ACCESS_KEY": "YOUR_ACCESS_KEY"
  }
}
```

OpenClaw 会自动将 `env.ACCESS_KEY` 注入到运行环境；请求时需在 Header 中携带 `accessKey`。若未配置或 `ACCESS_KEY` 为空，请求将鉴权失败。

**与 openclaw.json 的对应关系：**

| openclaw.json 路径 | 含义 |
|--------------------|------|
| `skills.entries["web-search"].enabled` | 是否启用本技能 |
| `skills.entries["web-search"].apiKey` | 技能 API 密钥（与 ACCESS_KEY 同值） |
| `skills.entries["web-search"].env.ACCESS_KEY` | 请求头 `accessKey` 的实际取值 |

---

## 使用场景

当用户提出以下需求时，应优先使用本技能：

- 需要 **检索互联网上的最新信息**
- 查询 **具体事实、数据或文档**
- 做 **技术调研、竞品或资料搜集**
- 需要 **引用网页链接或摘要** 作为依据

---

## 接口说明

### 基本信息

- **URL**：`https://open.bohrium.com/openapi/v1/search/web`
- **Method**：GET
- **Auth**：Header 中携带 `accessKey`（来自 `env.ACCESS_KEY`）
- **Rate Limit**：继承全局 v1 限流

> `engine`、`api_key` 等由网关固定为 `engine=google`，调用方无需传入。

### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 默认值 | 取值范围 |
|--------|------|------|------|--------|----------|
| `q` | string | 是 | 搜索关键词 | - | 非空 |
| `num` | int | 否 | 返回结果数量 | 3 | 1–10 |

### 请求示例

**Headers**

```json
{
  "accessKey": "$ACCESS_KEY"
}
```

**curl**

```bash
curl -G "https://open.bohrium.com/openapi/v1/search/web" \
  -H "accessKey: your_access_key_here" \
  --data-urlencode "q=OpenAI latest models" \
  --data-urlencode "num=5"
```

### 成功响应

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "results": [
      {
        "title": "OpenAI – Latest models",
        "link": "https://openai.com/",
        "snippet": "Discover the newest GPT models and API updates..."
      }
    ],
    "search_information": {
      "query_displayed": "OpenAI latest models",
      "total_results": 1230000
    }
  }
}
```

### 失败响应

上游搜索接口异常时可能返回：

```json
{
  "code": 5000,
  "message": "Upstream service error",
  "error": "search upstream error: status 429",
  "request_id": "trace-id"
}
```

---

## 注意事项

- **ACCESS_KEY 必填**：在 `~/.openclaw/openclaw.json` 的 `skills.entries["web-search"]` 中配置 `apiKey` 与 `env.ACCESS_KEY`。
- 必须携带 `accessKey` 请求头，**不会产生计费**。
- **限流**：受全局 v1 限流约束。
- `num` 建议不超过 10，超出将被自动截断为 10。
- 返回结果来自 searchapi.io，字段可能随上游演进；上游错误时可能返回 `code: 5000`（如 429 等）。

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 鉴权失败 / 401 | ACCESS_KEY 未配置或错误 | 在 openclaw.json 中正确配置 `apiKey` 与 `env.ACCESS_KEY` |
| `code: 5000` | 上游搜索服务异常（如 429） | 稍后重试或减少请求频率 |
| 结果为空 | 关键词过窄或上游无结果 | 调整 `q` 或增加 `num` |
| `num` 无效 | 超过 10 会被截断 | 将 `num` 设为 1–10 |
