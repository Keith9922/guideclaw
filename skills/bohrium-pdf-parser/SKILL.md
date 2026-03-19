---
name: bohrium-pdf-parser
description: "Parse PDF documents via openapi.dp.tech. Use when: user asks about extracting text, tables, charts, formulas, or molecules from PDF files on Bohrium, submitting PDFs by URL or file upload. NOT for: file management, dataset management, or knowledge base operations."
---

# SKILL: Bohrium PDF 解析

## 概述

使用 `openapi.dp.tech` 提供的 PDF 解析服务，从 PDF 中提取文本、表格、图表、公式、分子式等内容。支持两种提交方式：

- **URL 提交** — 传入 PDF 下载链接（如 arXiv 链接）
- **文件上传** — 上传本地 PDF 文件

**无 CLI 支持** — 全部通过 HTTP API 操作。

## 认证配置

ACCESS_KEY 从 OpenClaw 配置文件 `~/.openclaw/openclaw.json` 中读取：

```json
"bohrium-pdf-parser": {
  "enabled": true,
  "apiKey": "YOUR_ACCESS_KEY",
  "env": {
    "ACCESS_KEY": "YOUR_ACCESS_KEY"
  }
}
```

OpenClaw 会自动将 `env.ACCESS_KEY` 注入到运行环境。

## 通用代码模板

```python
import os, time, requests

AK = os.environ.get("ACCESS_KEY", "")
BASE = "https://openapi.dp.tech/openapi/v1/parse"
HEADERS = {"accessKey": AK}
HEADERS_JSON = {**HEADERS, "Content-Type": "application/json"}
```

> **注意**: API 服务在 `openapi.dp.tech`。`open.bohrium.com` 仅为文档站点（Apifox 托管），不是 API 地址。

---

## 解析工作流

```
1. 提交 PDF（URL 或文件上传）→ 获得 token
2. 用 token 轮询结果 → status == "success" 时完成
```

同步模式（`sync=true`）提交后等待解析完成再返回，但不含 content，仍需调用 `get-result` 获取；异步模式（`sync=false`，默认）需要轮询 `get-result` 等待 status 变为 `success`。

---

## URL 提交解析

```python
r = requests.post(f"{BASE}/trigger-url-async", headers=HEADERS_JSON, json={
    "url": "https://arxiv.org/pdf/2107.06922",
    "sync": False,
    "textual": True,
    "table": True,
    "molecule": True,
    "chart": True,
    "figure": False,
    "expression": True,
    "equation": True,
    "pages": [0],           # 0-indexed，省略则解析全部页
    "timeout": 1800
})
data = r.json()
token = data["token"]
print(f"Token: {token}, Status: {data['status']}")
# Token: 57d12c5a-..., Status: undefined
```

**响应字段：**

| 字段 | 说明 |
|------|------|
| `token` | 任务标识，用于查询结果 |
| `status` | 初始状态为 `undefined` |
| `created_time` | 创建时间 |
| `time_dict` | 各阶段耗时（此时仅含 `download_pdf`） |

---

## 文件上传解析

```python
from pathlib import Path

pdf_path = Path("./paper.pdf")
with open(pdf_path, "rb") as f:
    r = requests.post(f"{BASE}/trigger-file-async",
        headers=HEADERS,       # 不设 Content-Type，requests 自动处理 multipart
        files={"file": (pdf_path.name, f, "application/pdf")},
        data={
            "sync": "false",
            "textual": "true",
            "table": "true",
            "molecule": "true",
            "chart": "true",
            "figure": "false",
            "expression": "true",
            "equation": "true",
            "pages": 0,         # multipart 中只能传单个整数
            "timeout": 1800
        })
token = r.json()["token"]
```

> **关键**：`pages` 在 multipart/form-data 中只能传**单个整数**（如 `0`），不能传 JSON 数组 `[0]`，否则报 `int_parsing` 错误。JSON 请求体中可以传数组 `[0, 1, 2]`。

---

## 查询解析结果

```python
r = requests.post(f"{BASE}/get-result", headers=HEADERS_JSON, json={
    "token": token,
    "content": True,        # 返回解析出的文本
    "objects": False,        # 返回解析出的对象（表格、图等）
    "pages_dict": True       # 按页返回结果
})
data = r.json()
print(f"Status: {data['status']}, Content length: {len(data.get('content', ''))}")
```

**响应字段：**

| 字段 | 说明 |
|------|------|
| `status` | `success` / `undefined`（处理中）/ `failed` |
| `token` | 任务标识 |
| `content` | 解析出的文本（LaTeX 标记格式） |
| `pages_dict` | 按页的解析结果字典 |
| `lang` | 检测到的语言（`en` / `zh` 等） |
| `proc_page` / `total_page` | 已处理/总页数 |
| `proc_textual` / `total_textual` | 已处理/总文本块数 |
| `proc_table` / `total_table` | 已处理/总表格数 |
| `proc_mol` / `total_mol` | 已处理/总分子式数 |
| `proc_equa` / `total_equa` | 已处理/总公式数 |
| `time_dict` | 各阶段耗时详情 |
| `cost` | 费用 |

---

## 异步轮询完整示例

```python
import os, time, requests

AK = os.environ.get("ACCESS_KEY", "")
BASE = "https://openapi.dp.tech/openapi/v1/parse"
HEADERS = {"accessKey": AK}
HEADERS_JSON = {**HEADERS, "Content-Type": "application/json"}

# 1. 提交
r = requests.post(f"{BASE}/trigger-url-async", headers=HEADERS_JSON, json={
    "url": "https://arxiv.org/pdf/2107.06922",
    "sync": False,
    "textual": True, "table": True, "molecule": False,
    "chart": False, "figure": False,
    "expression": True, "equation": True,
    "pages": [0],
    "timeout": 1800
})
submit = r.json()
if submit.get("code"):
    print(f"Submit failed: {submit.get('message')}")
    exit(1)

token = submit["token"]
print(f"Submitted, token={token}")

# 2. 轮询结果
for attempt in range(30):
    time.sleep(2)
    r = requests.post(f"{BASE}/get-result", headers=HEADERS_JSON, json={
        "token": token,
        "content": True,
        "objects": False,
        "pages_dict": False
    })
    result = r.json()
    status = result.get("status", "")
    print(f"  [{attempt+1}] status={status}")

    if status == "success":
        print(f"Done! Content length: {len(result.get('content', ''))}")
        print(f"Language: {result.get('lang')}, Cost: {result.get('cost')}")
        print(f"Preview: {result.get('content', '')[:200]}")
        break
    elif status == "failed":
        print(f"Failed: {result.get('description', 'unknown error')}")
        break
else:
    print("Timeout: task did not complete within 60 seconds")
```

---

## 同步模式示例

同步模式（`sync=true`）提交后等待解析完成再返回，无需轮询状态。但**返回中不含 content 字段**，仍需调用 `get-result` 获取解析内容：

```python
# 1. 同步提交 — 阻塞等待解析完成
r = requests.post(f"{BASE}/trigger-url-async", headers=HEADERS_JSON, json={
    "url": "https://arxiv.org/pdf/2107.06922",
    "sync": True,           # 同步等待完成
    "textual": True, "table": True,
    "molecule": False, "chart": False, "figure": False,
    "expression": True, "equation": True,
    "pages": [0],
    "timeout": 1800
})
submit = r.json()
token = submit["token"]
# submit["status"] == "success"，但不含 content

# 2. 获取内容
r = requests.post(f"{BASE}/get-result", headers=HEADERS_JSON, json={
    "token": token,
    "content": True, "objects": False, "pages_dict": False
})
result = r.json()
print(f"Content: {result['content'][:200]}")
```

---

## 解析选项说明

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `sync` | bool | `false` | `true` 等待解析完成再返回（仍需 `get-result` 取 content），`false` 需轮询 |
| `textual` | bool | - | 解析文本内容 |
| `table` | bool | - | 解析表格 |
| `molecule` | bool | - | 解析分子式 |
| `chart` | bool | - | 解析图表 |
| `figure` | bool | - | 解析图像 |
| `expression` | bool | - | 解析数学表达式 |
| `equation` | bool | - | 解析公式 |
| `pages` | list[int] | 全部 | 指定解析页码（0-indexed） |
| `timeout` | int | - | 超时时间（秒） |

---

## curl 示例

```bash
AK="YOUR_ACCESS_KEY"
BASE="https://openapi.dp.tech/openapi/v1/parse"

# URL 提交
curl -s -X POST "$BASE/trigger-url-async" \
  -H "Content-Type: application/json" \
  -H "accessKey: $AK" \
  -d '{"url":"https://arxiv.org/pdf/2107.06922","sync":false,"textual":true,"table":true,"molecule":false,"chart":false,"figure":false,"expression":true,"equation":true,"pages":[0],"timeout":1800}'

# 文件上传
curl -s -X POST "$BASE/trigger-file-async" \
  -H "accessKey: $AK" \
  -F "file=@paper.pdf" \
  -F "sync=false" -F "textual=true" -F "table=true" \
  -F "pages=0"

# 查询结果
curl -s -X POST "$BASE/get-result" \
  -H "Content-Type: application/json" \
  -H "accessKey: $AK" \
  -d '{"token":"YOUR_TOKEN","content":true,"objects":false,"pages_dict":true}'
```

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `AccessKey is required` | 未传或传错 accessKey | Header 名为 `accessKey`（注意大小写），不是 `Authorization: Bearer` |
| `int_parsing` 错误 | 文件上传时 `pages` 传了 JSON 数组 | multipart form 中 `pages` 只能传单个整数 |
| `status: undefined` | 异步任务尚未完成 | 等待后重新调用 `get-result`，建议间隔 2 秒轮询 |
| 连接超时 | 使用了错误的域名 | 确认用 `openapi.dp.tech`，不是 `open.bohrium.com` |
| content 含 LaTeX 标记 | 正常行为 | 解析结果用 `\begin{title}` 等标记段落结构，需后处理提取纯文本 |
| 大文件解析慢 | 页数多或内容复杂 | 用 `pages` 参数指定需要的页码，减少解析范围 |
