---
name: bohrium-knowledge-base
description: "Manage Bohrium knowledge bases via openapi.dp.tech API. Use when: user asks about creating/listing/searching knowledge bases, managing literature/papers, uploading files, tagging, notes, or searching literature content. NOT for: compute jobs, nodes, images, or datasets."
---

# SKILL: Bohrium 知识库 (Knowledge Base) 管理

## 概述

管理 Bohrium 平台的知识库（Literature Sage）。知识库提供文献管理、文件夹组织、标签分类、笔记、文献内容搜索与召回、权限管理等功能。

**无 CLI 支持** — 与 bohrium-job/node/image 等不同，知识库没有 `bohr` CLI 命令，全部通过 HTTP API 操作。

## 认证配置

ACCESS_KEY 从 OpenClaw 配置文件 `~/.openclaw/openclaw.json` 中读取：

```json
"bohrium-knowledge-base": {
  "enabled": true,
  "apiKey": "YOUR_ACCESS_KEY",
  "env": {
    "ACCESS_KEY": "YOUR_ACCESS_KEY"
  }
}
```

OpenClaw 会自动将 `env.ACCESS_KEY` 注入到运行环境。

## 路由映射

```
外部调用: GET/POST https://openapi.dp.tech/openapi/v1/knowledge/{path}
         Header: accessKey: YOUR_ACCESS_KEY

网关转发: → literature-sage.bohrium.com/api/v1/{path}
         Header: X-User-Id, X-Org-Id (由 accessKey 自动转换)
```

## 通用代码模板

```python
import os, requests

AK = os.environ.get("ACCESS_KEY", "")
BASE = "https://openapi.dp.tech/openapi/v1/knowledge"
HEADERS = {"accessKey": AK}
HEADERS_JSON = {**HEADERS, "Content-Type": "application/json"}
```

---

## 知识库管理

### 创建知识库

```python
r = requests.post(f"{BASE}/knowledge_base/create", headers=HEADERS_JSON, json={
    "knowledgeBaseName": "My Knowledge Base",
    "cover": "",
    "introduction": "A collection of papers on molecular dynamics",
    "privilege": 1  # 1=私有, 2=公开
})
print(r.json())
# {"code": 0, "data": {"id": 123, "msg": "Knowledge base created successfully."}}
```

**参数说明：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `knowledgeBaseName` | string | 是 | 知识库名称 |
| `cover` | string | 是 | 封面图 URL（可为空字符串） |
| `introduction` | string | 是 | 知识库简介 |
| `privilege` | integer | 是 | 1=私有, 2=公开 |

### 我的知识库列表

```python
r = requests.get(f"{BASE}/knowledge_base/list", headers=HEADERS,
    params={"keyword": "", "pageSize": 10, "pageNum": 1})
data = r.json()["data"]
for kb in data["list"]:
    print(f"[{kb['id']}] {kb['name']} (nodeId={kb['nodeId']}, privilege={kb['privilege']})")
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `keyword` | string | 否 | 搜索关键字 |
| `pageSize` | integer | 否 | 每页条数（默认 10） |
| `pageNum` | integer | 否 | 页码（默认 1） |

**返回字段：**

| 字段 | 说明 |
|------|------|
| `id` | 知识库 ID |
| `name` | 知识库名称 |
| `nodeId` | 知识库节点 ID（用于查询文献、文件夹操作） |
| `introduction` | 简介 |
| `cover` | 封面 URL |
| `privilege` | 1=私有, 2=公开 |
| `isZotero` | 是否 Zotero 同步知识库 |
| `count` | 文献数量 |
| `updateTime` | 更新时间（ISO 8601） |
| `createTime` | 创建时间（ISO 8601） |
| `source` | 来源标识 |
| `favoriteCount` | 收藏数 |
| `sessionCount` | 会话数 |

### 更新知识库

```python
r = requests.post(f"{BASE}/knowledge_base/update", headers=HEADERS_JSON, json={
    "knowledgeBaseName": "Updated Name",
    "cover": "",
    "introduction": "Updated introduction",
    "NodesId": 456,       # 知识库节点 ID
    "privilege": 2         # 改为公开
})
# {"code": 0, "data": {"id": 123, "msg": "Knowledge base updated successfully."}}
```

### 知识库详情

```python
node_id = 456
r = requests.get(f"{BASE}/knowledge_base/{node_id}", headers=HEADERS)
print(r.json())
```

### 发现公开知识库

```python
r = requests.get(f"{BASE}/knowledge_base/discover", headers=HEADERS,
    params={"pageSize": 10, "pageNum": 1})
```

### 搜索知识库

```python
r = requests.get(f"{BASE}/knowledge_base/search", headers=HEADERS,
    params={"keyword": "molecular dynamics"})
```

### 转存知识库

```python
r = requests.post(f"{BASE}/knowledge_base/copy", headers=HEADERS_JSON, json={
    "knowledgeBaseId": 123
})
```

---

## 文件夹管理

### 根目录列表（知识库列表）

```python
r = requests.get(f"{BASE}/folder/root", headers=HEADERS)
data = r.json()["data"]
print(f"共 {data['total']} 个知识库, {data['docCount']} 篇文献")
for item in data["list"]:
    print(f"  [{item['id']}] {item['name']} ({item['docCount']} 篇, "
          f"relationship={'拥有' if item['relationship'] == 1 else '加入'})")
```

**返回字段：**

| 字段 | 说明 |
|------|------|
| `total` | 知识库数量 |
| `list[].id` | 文件夹/知识库 ID |
| `list[].name` | 名称 |
| `list[].docCount` | 文献数量 |
| `list[].relationship` | 1=拥有该知识库, 2=已加入 |
| `docCount` | 总文献数 |

### 子目录列表（一级）

```python
r = requests.get(f"{BASE}/folder/children", headers=HEADERS,
    params={"folderId": 456, "pageNum": 1, "pageSize": 20})
data = r.json()["data"]

# 路径面包屑
for p in data["path"]:
    print(f"  {'>' * p['depth']} {p['name']} (id={p['nodesId']})")

# 子文件夹
for f in data["subFolders"]:
    print(f"  [DIR] {f['name']} ({f['docCount']} 篇)")

# 文献
for f in data["files"]:
    print(f"  [FILE] {f['name']} | {f['fileName']} | {f['date']}")
```

**返回字段：**

| 字段 | 说明 |
|------|------|
| `path[]` | 路径面包屑 `{nodesId, name, depth}` |
| `subFolders[]` | 子文件夹 `{nodesId, name, docCount, createdTime}` |
| `files[]` | 文献列表 |
| `files[].nodesId` | 文献节点 ID |
| `files[].paperId` | 论文 ID |
| `files[].md5` | 文件 MD5 |
| `files[].enName` | 英文标题 |
| `files[].zhName` | 中文标题 |
| `files[].fileName` | 文件名 |
| `files[].authors` | 作者列表 |
| `files[].date` | 发表日期 |
| `files[].literatureType` | 文献类型 |
| `fileCount` | 文件总数 |

### 目录树

```python
r = requests.get(f"{BASE}/folder/directory", headers=HEADERS,
    params={"folderId": 456})
# 递归树结构: [{nodesId, name, subFolders: [{nodesId, name, subFolders: [...]}]}]
```

### 创建文件夹

```python
r = requests.post(f"{BASE}/folder/create", headers=HEADERS_JSON, json={
    "parentId": 456,             # 父文件夹 ID
    "folderName": "My Folder"
})
# {"code": 0, "data": {"message": "..."}}
```

### 重命名文件夹

```python
r = requests.post(f"{BASE}/folder/update", headers=HEADERS_JSON, json={
    "nodesId": 789,              # 文件夹节点 ID
    "folderName": "New Name"
})
```

### 移动文件夹

```python
r = requests.post(f"{BASE}/folder/move", headers=HEADERS_JSON, json={
    "sourceFolderId": 789,       # 源文件夹 ID
    "targetFolderId": 456        # 目标文件夹 ID
})
```

### 删除文件夹

```python
r = requests.post(f"{BASE}/folder/delete", headers=HEADERS_JSON, json={
    "nodesId": 789
})
```

---

## 文献管理

### 文献列表

```python
r = requests.get(f"{BASE}/file", headers=HEADERS,
    params={
        "parentId": 456,        # 文件夹 ID
        "pageNum": 1,
        "pageSize": 20,
        "order": "desc",        # asc / desc
        "orderBy": "createdTime",
        "noTag": False          # True 只看未打标签的
    })
```

### 文献详情

```python
r = requests.get(f"{BASE}/file/detail", headers=HEADERS,
    params={"resourceId": "12345"})
detail = r.json()["data"]
print(f"标题: {detail['enName']}")
print(f"作者: {', '.join(a['name'] for a in detail.get('authorDetails', []))}")
print(f"DOI: {detail.get('doi', '')}")
print(f"摘要: {detail.get('enAbstract', '')}")
```

**返回字段（精选）：**

| 字段 | 说明 |
|------|------|
| `id` | 文献 ID |
| `enName` / `zhName` | 英文/中文标题 |
| `authors` | 作者列表 |
| `authorDetails[]` | 作者详情（含 scholarId, avatar, name, paperNums, citationNums, hIndex） |
| `doi` | DOI |
| `enAbstract` / `zhAbstract` | 英文/中文摘要 |
| `date` | 发表日期 |
| `fileName` | 文件名 |
| `md5` | 文件 MD5 |
| `paperId` | 论文 ID |
| `publicationEnName` | 期刊名 |
| `literatureType` | 文献类型 |
| `openAccess` | 是否开放获取 |
| `existPDF` | 是否有 PDF |
| `summary[]` | 章节摘要 `{title, zhTitle, content, zhContent}` |

### 文献下载链接

```python
r = requests.post(f"{BASE}/file/read", headers=HEADERS_JSON, json={
    "resourceId": 12345
})
# 返回下载链接
```

### 导入文献

```python
r = requests.post(f"{BASE}/file/submit", headers=HEADERS_JSON, json={
    "parentId": 456,
    "fileName": "paper.pdf",
    "md5": "abc123...",
    "size": 1024000,
    "url": "https://..."        # 文件上传后的 URL
})
```

### 编辑文献信息

```python
r = requests.post(f"{BASE}/file/edit", headers=HEADERS_JSON, json={
    "id": 12345,
    "name": '{"cn":"中文标题","en":"English Title"}',
    "doi": "10.1234/example",
    "authors": '["Author A","Author B"]',
    "date": "2024-01-15",
    "journal": "Nature",
    "abstract": '{"cn":"中文摘要","en":"English abstract"}',
    "importance": 1,
    "recallable": True,
    "unableRecallEnMsg": "",
    "unableRecallZhMsg": ""
})
```

**参数说明：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | integer | 是 | 文献 ID |
| `name` | string (JSON) | 是 | `{"cn":"...","en":"..."}` 格式 |
| `doi` | string | 是 | DOI |
| `authors` | string (JSON array) | 是 | `["Author A","Author B"]` 格式 |
| `date` | string | 是 | 日期 `YYYY-MM-DD` |
| `journal` | string | 是 | 期刊名 |
| `abstract` | string (JSON) | 是 | `{"cn":"...","en":"..."}` 格式 |
| `importance` | integer | 是 | 重要程度 |
| `recallable` | boolean | 是 | 是否可被召回 |
| `unableRecallEnMsg` | string | 是 | 不可召回原因（英文） |
| `unableRecallZhMsg` | string | 是 | 不可召回原因（中文） |

### 删除文献

```python
r = requests.post(f"{BASE}/file/delete_literature", headers=HEADERS_JSON, json={
    "resourceId": 12345
})
```

### 重命名文献

```python
r = requests.post(f"{BASE}/file/update_literature", headers=HEADERS_JSON, json={
    "resourceId": 12345,
    "name": "New Literature Name"
})
```

### 移动文献

```python
r = requests.post(f"{BASE}/file/move", headers=HEADERS_JSON, json={
    "resourceId": 12345,
    "targetFolderId": 789
})
```

### 文献内容搜索

```python
r = requests.post(f"{BASE}/file/search", headers=HEADERS_JSON, json={
    "queryContent": "molecular dynamics simulation",
    "nodesId": 456,
    "knowledgeBaseId": 123
})
data = r.json()["data"]
print(f"共找到 {data['total']} 条结果")
for f in data["Files"]:
    print(f"  [{f['userResourceId']}] {f['fileName']}: {f['content'][:100]}...")
```

**返回字段：**

| 字段 | 说明 |
|------|------|
| `total` | 匹配总数 |
| `Files[].userResourceId` | 文献 ID |
| `Files[].fileName` | 文件名 |
| `Files[].content` | 匹配内容片段 |
| `Files[].knowledgeBaseName` | 所属知识库名称 |

---

## 标签管理

### 标签列表

```python
r = requests.get(f"{BASE}/tag", headers=HEADERS,
    params={"keyword": ""})  # 可选关键字过滤
data = r.json()["data"]
for tag in data["list"]:
    print(f"  [{tag['id']}] {tag['name']} ({tag['count']} 篇)")
```

### 创建标签

```python
r = requests.post(f"{BASE}/tag", headers=HEADERS_JSON, json={
    "name": "Machine Learning"
})
tag = r.json()["data"]  # 注意：API 返回字段名可能为 "daya"
print(f"Created tag: {tag['id']} - {tag['name']}")
```

### 编辑标签

```python
r = requests.put(f"{BASE}/tag", headers=HEADERS_JSON, json={
    "tagId": 101,
    "name": "Deep Learning"
})
```

### 删除标签

```python
r = requests.delete(f"{BASE}/tag", headers=HEADERS_JSON, json={
    "tagId": 101
})
```

### 给文献打标签

```python
r = requests.post(f"{BASE}/file/tag", headers=HEADERS_JSON, json={
    "tagId": 101,
    "resourceId": 12345
})
```

### 取消文献标签

```python
r = requests.post(f"{BASE}/file/untag", headers=HEADERS_JSON, json={
    "tagId": 101,
    "resourceId": 12345
})
```

### 文献标签统计

```python
r = requests.get(f"{BASE}/file/tag", headers=HEADERS,
    params={
        "parentId": 456,       # 文件夹节点 ID（可选）
        "rootFolderId": 123,   # 知识库根文件夹 ID（可选）
        "query": 2,            # 1=按作者搜索, 2=按关键字搜索（可选）
        "keyword": "ML"        # 搜索关键字（可选）
    })
data = r.json()["data"]
print(f"总文献数: {data['allDocCount']}, 未打标签: {data['noTagCount']}")
for tag in data["tags"]:
    print(f"  [{tag['id']}] {tag['name']}: {tag['count']} 篇")
```

---

## 笔记

### 获取笔记

```python
r = requests.get(f"{BASE}/note", headers=HEADERS,
    params={"resourceId": 12345})
note = r.json()["data"]
print(f"笔记内容: {note['note']}")
```

### 创建/更新笔记

```python
r = requests.post(f"{BASE}/note", headers=HEADERS_JSON, json={
    "resourceId": 12345,
    "note": "This paper introduces a novel approach to..."
})
# {"code": 0}
```

---

## 文献召回与搜索

### 文献切片查看

查看特定文献的解析切片结果：

```python
r = requests.post(f"{BASE}/box/search_by_md5_paper_id", headers=HEADERS_JSON, json={
    "md5": "abc123...",
    "paper_id": "paper_001",
    "page_num": 1,
    "page_size": 10
})
```

### 指定文献召回

在指定文献中进行语义召回：

```python
r = requests.post(f"{BASE}/recall/papers", headers=HEADERS_JSON, json={
    "query": "molecular dynamics force field",
    "paperIds": ["paper_001", "paper_002"],
    "topK": 5
})
```

### 混合召回（知识库级）

在整个知识库中进行混合语义搜索：

```python
r = requests.post(f"{BASE}/recall/hybrid", headers=HEADERS_JSON, json={
    "query": "deep potential energy surface",
    "knowledgeBaseId": 123,
    "topK": 10
})
```

---

## 权限管理

### 权限列表

```python
r = requests.get(f"{BASE}/account/acl", headers=HEADERS,
    params={"knowledgeBaseId": 123})
```

### 设置分享状态

```python
r = requests.post(f"{BASE}/account/share_status", headers=HEADERS_JSON, json={
    "knowledgeBaseId": 123,
    "shareStatus": 1  # 1=开启分享, 0=关闭
})
```

### 更新用户权限

```python
r = requests.post(f"{BASE}/account/user_role", headers=HEADERS_JSON, json={
    "knowledgeBaseId": 123,
    "userId": 456,
    "role": 2  # 见下方角色说明
})
```

### 删除用户权限

```python
r = requests.delete(f"{BASE}/account/user_role", headers=HEADERS_JSON, json={
    "knowledgeBaseId": 123,
    "userId": 456
})
```

### 批量添加读者

```python
r = requests.post(f"{BASE}/account/batch_add_readers", headers=HEADERS_JSON, json={
    "knowledgeBaseId": 123,
    "userIds": [456, 789, 1011]
})
```

### 申请加入知识库

```python
r = requests.post(f"{BASE}/account/join_request", headers=HEADERS_JSON, json={
    "knowledgeBaseId": 123
})
```

### 查询用户角色

```python
r = requests.get(f"{BASE}/account/user_knowledge_base_role", headers=HEADERS,
    params={"knowledgeBaseId": 123})
```

---

## 权限角色说明

| 角色值 | 角色 | 权限 |
|--------|------|------|
| 1 | 拥有者 (Owner) | 完全控制：增删改查、权限管理、删除知识库 |
| 2 | 编辑者 (Editor) | 增删改查文献、管理标签和文件夹 |
| 3 | 阅读者 (Reader) | 只读：查看文献、下载、搜索 |

**知识库可见性（privilege）：**

| 值 | 说明 |
|----|------|
| 1 | 私有 — 仅拥有者和被授权用户可见 |
| 2 | 公开 — 所有人可发现和查看 |

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `code` 非 0 | API 调用错误 | 检查返回的 `message` 字段获取具体错误信息 |
| 401 Unauthorized | accessKey 无效或过期 | 确认 ACCESS_KEY 正确 |
| 找不到知识库 | 使用了错误的 ID | `nodeId`（节点 ID）和 `id`（知识库 ID）是不同概念，根据 API 要求使用正确的 ID |
| 文献搜索无结果 | 文献尚未完成索引 | 新导入的文献需要等待后台解析和索引完成 |
| 编辑文献 name/abstract 格式错误 | 需要 JSON 字符串 | `name` 和 `abstract` 字段需要传 JSON 字符串如 `'{"cn":"...","en":"..."}'` |
| 创建标签返回 `daya` | API 已知 typo | 返回中 `daya` 等同于 `data`，可直接使用 |
| 文件夹操作报权限错误 | 角色权限不足 | 需要编辑者(2)或拥有者(1)角色才能修改 |
