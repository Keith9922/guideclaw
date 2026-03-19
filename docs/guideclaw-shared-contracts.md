# 引路虾共享数据契约（草案）

> 用于前端、后端、RAG、OpenClaw skills 的最小对齐。第一版先稳定字段，再逐步扩展。

## Project

```json
{
  "id": "proj_oled_001",
  "title": "机器学习辅助 OLED 材料筛选",
  "stage": "literature_review",
  "summary": "面向科研新人的 OLED 方向前期调研项目"
}
```

## LiteratureCard

```json
{
  "id": "lit_001",
  "title": "Sample Paper",
  "research_question": "该工作想解决什么问题",
  "method": "所用方法",
  "data_source": "数据来源",
  "key_result": "核心结果",
  "limitations": ["局限 1", "局限 2"],
  "evidence": [
    {
      "source": "paper-1.pdf",
      "page": 3,
      "snippet": "原文证据片段"
    }
  ]
}
```

## GapCard

```json
{
  "id": "gap_001",
  "title": "候选研究缺口",
  "gap_type": "方法缺陷",
  "why_it_matters": "为什么重要",
  "novelty_score": 7,
  "importance_score": 8,
  "feasibility_score": 6,
  "evidence": [
    {
      "source": "review.pdf",
      "page": 5,
      "snippet": "相关证据"
    }
  ]
}
```

## PlanCard

```json
{
  "id": "plan_001",
  "research_question": "研究问题",
  "boundary": "研究边界",
  "data_source": "数据来源",
  "metrics": ["MAE", "R2"],
  "methods": ["基线模型", "图模型"],
  "validation": "验证思路"
}
```

## MeetingNote

```json
{
  "id": "note_001",
  "decisions": ["结论 1", "结论 2"],
  "open_questions": ["未解决问题 1"],
  "todos": ["待办 1", "待办 2"],
  "next_step": "下一步研究推进方向"
}
```

