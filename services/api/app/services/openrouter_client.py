from __future__ import annotations

import json
from textwrap import dedent
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.domain.schemas import ArtifactBundle, KnowledgeSource, Project, ProjectState
from app.settings import Settings

MODEL_ALIASES = {
    "openrouter/healer-alpha": "xiaomi/mimo-v2-omni",
    "healer-alpha": "xiaomi/mimo-v2-omni",
}
FREE_MODEL_FALLBACKS = ["openrouter/free"]


def _model_candidates(model: str) -> list[str]:
    candidates: list[str] = [model]
    aliased = MODEL_ALIASES.get(model)
    if aliased and aliased not in candidates:
        candidates.append(aliased)
    for fallback in FREE_MODEL_FALLBACKS:
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


def build_project_context(project: Project, artifacts: ArtifactBundle) -> str:
    literature_lines = [
        f"- {card.title}｜问题：{card.research_question}｜方法：{card.method}｜结果：{card.key_result}"
        for card in artifacts.literature_cards
    ]
    gap_lines = [
        f"- {card.title}｜类型：{card.gap_type}｜原因：{card.why_it_matters}"
        for card in artifacts.gap_cards
    ]
    plan_lines = [
        f"- 研究问题：{card.research_question}｜边界：{card.boundary}｜验证：{card.validation}"
        for card in artifacts.plan_cards
    ]
    note_lines = [
        f"- 结论：{'；'.join(card.decisions)}｜下一步：{card.next_step}"
        for card in artifacts.meeting_notes
    ]

    return dedent(
        f"""
        项目标题：{project.title}
        项目阶段：{project.stage}
        项目摘要：{project.summary or '暂无'}

        文献卡：
        {chr(10).join(literature_lines) if literature_lines else '- 暂无'}

        缺口卡：
        {chr(10).join(gap_lines) if gap_lines else '- 暂无'}

        方案卡：
        {chr(10).join(plan_lines) if plan_lines else '- 暂无'}

        纪要卡：
        {chr(10).join(note_lines) if note_lines else '- 暂无'}
        """
    ).strip()


async def generate_project_summary(
    settings: Settings,
    project: Project,
    artifacts: ArtifactBundle,
) -> tuple[str, str]:
    if not settings.openrouter_ready or not settings.openrouter_api_key or not settings.openrouter_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenRouter is not fully configured",
        )

    return await generate_text(
        settings,
        system_prompt=(
            "你是“引路虾”的研究导航层，不暴露底层模型、供应商或任何技术品牌。"
            "你的身份是冷静、可靠的科研导师助理，擅长把零散信息整理成适合科研新人的可执行结论。"
            "请基于给定项目和结构化产物，输出一段简明、可信、适合科研新人的中文摘要。"
            "重点包括：当前研究主题、前人工作概况、推荐研究缺口、建议下一步。"
            "避免夸张，不要编造未提供的事实，不要提及自己是某个模型。"
        ),
        user_prompt=build_project_context(project, artifacts),
    )


async def _request_openrouter(
    settings: Settings,
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    response_format: dict[str, Any] | None = None,
) -> tuple[str, str]:
    if not settings.openrouter_ready or not settings.openrouter_api_key or not settings.openrouter_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenRouter is not fully configured",
        )

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "GuideClaw",
    }

    actual_model = settings.openrouter_model
    response: httpx.Response | None = None
    async with httpx.AsyncClient(timeout=60) as client:
        for candidate in _model_candidates(settings.openrouter_model):
            payload["model"] = candidate
            response = await client.post(
                f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            if response.status_code >= 400 and response_format is not None:
                fallback_payload = dict(payload)
                fallback_payload.pop("response_format", None)
                fallback_payload["messages"] = [
                    {"role": "system", "content": f"{system_prompt}\n\n你必须只输出指定格式的内容。"},
                    {"role": "user", "content": user_prompt},
                ]
                response = await client.post(
                    f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=fallback_payload,
                )
            if response.status_code in {402, 404, 429} and candidate != _model_candidates(settings.openrouter_model)[-1]:
                continue
            actual_model = candidate
            break

    if response is None or response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "OpenRouter request failed",
                "status_code": response.status_code if response else None,
                "body": response.text if response else "no response",
            },
        )

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return actual_model, content


async def generate_text(
    settings: Settings,
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
) -> tuple[str, str]:
    return await _request_openrouter(
        settings,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
    )


async def translate_text(settings: Settings, text: str) -> tuple[str, str]:
    return await generate_text(
        settings,
        system_prompt=(
            "你是科研文本翻译助手。"
            "请把用户给出的英文或中英混排文本翻译成自然、准确、专业的简体中文。"
            "保留论文标题、专有名词、缩写、DOI、链接和 Markdown 结构。"
            "不要额外解释，不要添加前言，只返回翻译后的中文。"
        ),
        user_prompt=text,
        temperature=0,
    )


def build_follow_up_context(
    project: Project,
    state: ProjectState,
    artifacts: ArtifactBundle,
    knowledge_sources: list[KnowledgeSource],
    question: str,
) -> str:
    source_lines = [
        f"- {item.title}｜{item.venue or '未知来源'}｜{item.doi or item.url or '无外链'}"
        for item in knowledge_sources[:6]
    ] or ["- 暂无知识源"]
    return dedent(
        f"""
        用户追问：{question}

        项目标题：{project.title}
        项目摘要：{project.summary or '暂无'}
        当前阶段：{project.stage}
        当前研究焦点：{state.research_focus or '暂无'}
        当前假设：{state.current_hypothesis or '暂无'}
        当前下一步：{state.next_step or '暂无'}

        已有文献卡：{len(artifacts.literature_cards)}
        已有缺口卡：{len(artifacts.gap_cards)}
        已有方案卡：{len(artifacts.plan_cards)}
        已有纪要卡：{len(artifacts.meeting_notes)}

        当前知识源：
        {chr(10).join(source_lines)}
        """
    ).strip()


async def plan_follow_up(
    settings: Settings,
    *,
    project: Project,
    state: ProjectState,
    artifacts: ArtifactBundle,
    knowledge_sources: list[KnowledgeSource],
    question: str,
) -> tuple[str, dict[str, Any]]:
    model, content = await _request_openrouter(
        settings,
        system_prompt=(
            "你是引路虾里的 PI（课题负责人）。"
            "你要根据用户的追问决定下一轮该怎么推进，并优先只选择最关键的 1 个子角色去执行。"
            "只有在单个角色无法覆盖任务时，才可以选择第 2 个角色。"
            "可选角色只有：literature_assistant、gap_analyst、study_designer、meeting_secretary。"
            "请只输出 JSON，格式必须包含："
            '{"pi_focus":"...","delegates":[{"role":"literature_assistant","objective":"..."}],"why_this_plan":"..."}'
        ),
        user_prompt=build_follow_up_context(project, state, artifacts, knowledge_sources, question),
        response_format={"type": "json_object"},
    )
    return model, json.loads(content[content.find("{") : content.rfind("}") + 1])
