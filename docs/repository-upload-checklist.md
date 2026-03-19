# 引路虾上传仓库前建议清单

这份清单只解决一件事：

**在不泄露私密配置、不上传无关垃圾文件的前提下，把引路虾整理成一个完整、可读、可复现的项目仓库。**

## 一、建议上传的内容

以下内容建议保留并上传：

- `apps/`
- `services/`
- `skills/`
- `openclaw/`
- `docs/`
- `scripts/`
- `README.md`
- `package.json`
- `pnpm-workspace.yaml`
- `AGENTS.md`

这些内容构成了项目的完整主体：

- 前端工作台
- 后端 API 与工作流
- OpenClaw 角色技能
- 配置模板
- 演示文档与评审材料
- 本地启动和辅助脚本

## 二、建议不要上传的内容

以下内容不要进仓库：

- `.env`
- `.env.local`
- `services/api/.env.local`
- `apps/web/.env.local`
- 私有 API Key、Access Key、Token
- `~/.openclaw` 下的个人私有配置
- 本机缓存目录
- 临时截图以外的无关大文件
- 本地日志文件
- `node_modules`
- Python 虚拟环境目录
- 数据库里的敏感或测试数据

## 三、数据库怎么处理

数据库有 2 种策略。

### 策略 A：不上传真实数据库

适合更干净的开源仓库：

- 不上传 `data/guideclaw.db`
- 保留数据库初始化逻辑
- 保留 demo 项目生成逻辑
- 在 README 中说明如何本地启动并自动生成基础表

优点：

- 仓库最整洁
- 不会夹带脏数据
- 风险最小

### 策略 B：上传脱敏后的 demo 数据库

适合希望评委或同事“开箱就能看到效果”的场景：

- 上传一份脱敏后的 `guideclaw.db`
- 只保留 demo 项目，例如 OLED 示例
- 删除无关测试项目
- 删除无效 PDF、无意义知识源、临时测试文档

优点：

- 一启动就能看到完整效果
- 更适合演示和交接

当前建议：

**如果你的主要目标是比赛演示，建议保留一份脱敏后的 demo 数据库。**

## 四、上传前必须检查的项目

### 1. 文档入口是否完整

至少确认这些文件存在且可读：

- `README.md`
- `docs/final-demo-handoff.md`
- `docs/guideclaw-project-introduction.md`
- `docs/repository-upload-checklist.md`
- `docs/award-optimization-roadmap.md`

### 2. 关键链接是否可打开

确认 README 中提到的页面和文件真实存在。

### 3. 演示地址说明是否正确

当前默认地址应与 README 一致：

- Web：`http://127.0.0.1:3000`
- API：`http://127.0.0.1:8000`

### 4. 敏感信息是否已清理

重点检查：

- `.env.local`
- OpenRouter key
- Bohrium access key
- 任何硬编码 token

### 5. 结果汇总与 PDF 是否可用

至少确认：

- `/results?projectId=...`
- `/result-summary.pdf`

这两条链路要稳定。

## 五、上传前建议执行的检查命令

前端：

```bash
pnpm --filter @guideclaw/web typecheck
pnpm --filter @guideclaw/web build
```

后端：

```bash
python3 -m compileall services/api/app
```

OpenClaw：

```bash
GUIDECLAW_API_BASE_URL=http://127.0.0.1:8000 openclaw --profile guideclaw skills list
```

## 六、建议保留的演示资源

为了让仓库更像一个完整作品，建议保留：

- 评审文档中的 Mermaid 图
- 真实运行截图
- Logo 资源
- 结果汇总 PDF 导出能力

当前已经可以直接作为展示材料的截图：

- `docs/assets/guideclaw-workspace-demo-screen.png`
- `docs/assets/guideclaw-results-screen.png`
- `docs/assets/guideclaw-knowledge-screen.png`

## 七、仓库上传前最后一轮人工检查

上传前最后再确认：

- 这个仓库能不能让别人看明白“这是什么”
- 这个仓库能不能让别人看明白“怎么启动”
- 这个仓库能不能让别人看明白“最终交付是什么”
- 这个仓库是不是泄露了任何私有配置

如果这 4 个问题答案都没问题，这个仓库就已经不是“半成品”，而是一个完整项目仓库。
