---
name: preparation-agent
description: "Paper reproduction environment preparation skill. Use when: user needs to prepare reproduction environment, download code/data/models, install dependencies, or set up the workspace for a paper. NOT for: diagnosing reproducibility, planning reproduction steps, or scoring results."
---

# SKILL: 论文复现环境准备

根据论文 PDF 或诊断报告（Diagnose Agent 产出），自动下载并准备复现所需的全部资源（代码、数据、模型权重、依赖），完成后向用户汇报准备结果和目录结构。

> **重要**：本阶段仅负责**下载和配置已有资源**（开源代码、公开数据集、预训练权重、依赖安装等）。如果论文没有开源代码，**不要编写任何复现代码**，只需如实汇报并记录论文中的关键实现细节，留给后续编码阶段处理。

---

## 何时使用

当用户提到"准备复现环境"、"下载论文资源"、"准备代码和数据"等场景。

## PDF 解析

如需解析 PDF，使用 `bohrium-pdf-parser`。解析前先检查工作空间中是否已有解析结果（`.md`、`.txt`、`.json`），避免重复解析。

---

## 输入

接受以下任一形式：

1. **论文 PDF 文件路径** - 直接从 PDF 中提取代码仓库、数据集等信息
2. **诊断报告** - 来自 Diagnose Agent 的诊断结果（JSON 或 Markdown），其中已列出依赖清单
3. **用户口头描述** - 如"帮我准备 xxx 论文的复现环境"

---

## 工作流程

```
1. 解析论文/诊断报告 → 提取代码仓库、数据集、模型权重、依赖信息
       ↓
2. 下载代码 → git clone 或下载压缩包
       ↓
3. 下载数据集 → 从公开链接、Bohrium 数据集等获取
       ↓
4. 下载模型权重 → 预训练模型、checkpoint 等
       ↓
5. 安装依赖 → pip install / conda install / 系统包
       ↓
6. 汇报结果 → 告知用户准备完成情况和目录结构
```

### Step 1: 解析论文信息

- 若输入为 PDF：使用 `bohrium-pdf-parser` 或 `read` 解析论文，提取代码仓库 URL、数据集名称/链接、所需框架和依赖
- 若输入为诊断报告：直接从 `dependency_ledger` 中读取各类依赖
- 若信息不足：使用 `web_search` 搜索论文的官方代码仓库和数据集

### Step 2: 下载代码

- 优先 `git clone` 官方代码仓库
- 若仓库指定了特定 commit/tag/branch，切换到对应版本
- 若无官方仓库，搜索第三方实现并下载
- 若论文完全没有开源代码（官方和第三方均无）：跳过代码下载，在最终汇报中注明"无开源代码"，并从论文中提取关键实现信息（算法伪代码、网络结构、超参数、损失函数等）供后续编码阶段参考

### Step 3: 下载数据集

- 从论文或 README 中找到数据集下载链接
- 使用 `wget`/`curl` 或 Bohrium 数据集 API 下载
- 解压并放置到代码期望的目录位置

### Step 4: 下载模型权重（如需要）

- 下载预训练模型权重（HuggingFace、Google Drive、官方链接等）
- 放置到代码期望的模型目录

### Step 5: 安装依赖

- 检查 `requirements.txt`、`setup.py`、`environment.yml` 等依赖声明文件
- 执行 `pip install -r requirements.txt` 或对应的安装命令
- 安装系统级依赖（如有需要）

### Step 6: 汇报结果

准备完成后，**必须**向用户回复以下内容：

1. **准备状态** - 哪些资源已成功下载，哪些失败或跳过（及原因）
2. **目录结构** - 用树形结构展示工作目录的布局
3. **后续操作提示** - 如何开始运行、还需要用户手动完成的步骤（如有）

---

## 输出目录规范

所有资源统一放置在工作目录下，推荐结构：

```
<paper-name>/
├── code/                # 论文代码
│   ├── ...              # clone 下来的仓库内容
│   └── requirements.txt
├── data/                # 数据集
│   └── ...
├── models/              # 预训练模型权重（如有）
│   └── ...
└── README.md            # 准备说明（可选）
```

若代码仓库本身已包含 data/ 或 models/ 目录约定，则直接沿用代码仓库的目录结构。

---

## 汇报模板

```markdown
复现环境已准备完成！

已下载资源：
- 代码：[仓库名/来源]（commit: xxx）
- 数据集：[数据集名称]（大小: xxx）
- 模型权重：[模型名称]（大小: xxx）
- 依赖：已安装（pip install -r requirements.txt）

目录结构：
<paper-name>/
├── code/
│   └── ...
├── data/
│   └── ...
└── models/
    └── ...

注意事项：
- [需要用户关注的问题，如某个数据集需要手动申请权限等]
- [若论文无开源代码：注明"该论文无开源代码，需在后续阶段从零编写复现代码"]

论文实现要点（仅当无开源代码时提供）：
- 核心算法/网络结构描述
- 关键超参数
- 损失函数/优化器
- 其他复现所需的技术细节

接下来你可以：
- cd <paper-name>/code && python train.py  # 开始训练
- 或参考 code/README.md 了解具体运行方式
```

---

## 依赖的 Skills

| Skill | 用途 | 是否必需 |
|-------|------|----------|
| `bohrium-pdf-parser` | 输入为 PDF 时解析论文内容 | 推荐 |
| `bohrium-paper-search` | 搜索论文的代码仓库和数据集 | 推荐 |
| `bohrium-dataset` | 查询和下载 Bohrium 平台数据集 | 可选 |

---

## 错误处理

| 场景 | 处理 |
|------|------|
| 代码仓库不存在或私有 | 搜索第三方实现；若均无可用代码，如实告知用户并提取论文实现细节 |
| 数据集需要申请/付费 | 告知用户需要手动申请，提供申请链接 |
| 模型权重过大无法下载 | 告知用户文件大小，提供下载命令供手动执行 |
| 依赖安装失败 | 记录错误信息，尝试替代安装方式，汇报给用户 |
| PDF 无法解析 | 降级为 web_search 搜索论文信息 |

---

## 约束

- 只下载和配置已有资源，不编写复现代码
- 不外泄用户私有数据
