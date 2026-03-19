from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from textwrap import dedent
from typing import Any, Literal
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.domain.schemas import (
    AgentTask,
    ArtifactBundle,
    EvidenceSnippet,
    GapCard,
    KnowledgeChunk,
    KnowledgeSource,
    LiteratureCard,
    MeetingNote,
    PlanCard,
    Project,
    ProjectState,
    WorkflowStep,
    utc_now,
)
from app.services.bohrium_client import search_bohrium_papers
from app.services.knowledge_ingest import build_source_chunks
from app.services.knowledge_search import search_project_knowledge
from app.settings import Settings


OPENALEX_BASE_URL = "https://api.openalex.org"
MODEL_ALIASES = {
    "openrouter/healer-alpha": "xiaomi/mimo-v2-omni",
    "healer-alpha": "xiaomi/mimo-v2-omni",
}
FREE_MODEL_FALLBACKS = ["openrouter/free"]


class PrincipalInvestigatorDraft(BaseModel):
    current_stage: Literal["literature_review", "gap_analysis", "proposal", "meeting_notes"] = (
        "literature_review"
    )
    research_focus: str
    why_now: str
    key_questions: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)


def _normalize_stage(value: str | None) -> str:
    if not value:
        return "literature_review"
    normalized = value.strip().lower()
    stage_aliases = {
        "literature_review": "literature_review",
        "gap_analysis": "gap_analysis",
        "proposal": "proposal",
        "meeting_notes": "meeting_notes",
        "文献调研与问题识别": "literature_review",
        "文献调研": "literature_review",
        "文献梳理": "literature_review",
        "缺口分析": "gap_analysis",
        "方案设计": "proposal",
        "方案草拟": "proposal",
        "纪要沉淀": "meeting_notes",
    }
    return stage_aliases.get(value, stage_aliases.get(normalized, "literature_review"))


def _ensure_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = [
            segment.strip(" -\n\r\t")
            for segment in value.replace("；", "\n").replace(";", "\n").split("\n")
        ]
        return [part for part in parts if part]
    return [str(value).strip()]


def _ensure_single_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "；".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _normalize_score(value: Any) -> int:
    if value is None:
        return 0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if 0 <= numeric <= 1:
        numeric *= 10
    return max(0, min(10, int(round(numeric))))


def _sanitize_evidence(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    sanitized: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, str):
            sanitized.append(
                {
                    "source": "项目调查工作流",
                    "page": None,
                    "snippet": item,
                    "citation": None,
                    "doi": None,
                    "url": None,
                }
            )
            continue
        if isinstance(item, dict):
            sanitized.append(
                {
                    "source": str(item.get("source") or "项目调查工作流"),
                    "page": item.get("page"),
                    "snippet": str(item.get("snippet") or item.get("text") or "").strip(),
                    "citation": item.get("citation"),
                    "doi": item.get("doi"),
                    "url": item.get("url"),
                }
            )
    return [item for item in sanitized if item["snippet"]]


class LiteratureDraftCard(BaseModel):
    title: str
    research_question: str
    method: str
    data_source: str
    key_result: str
    limitations: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSnippet] = Field(default_factory=list)


class LiteratureDraft(BaseModel):
    literature_cards: list[LiteratureDraftCard] = Field(default_factory=list)


class GapDraftCard(BaseModel):
    title: str
    gap_type: str
    why_it_matters: str
    novelty_score: int = Field(ge=0, le=10)
    importance_score: int = Field(ge=0, le=10)
    feasibility_score: int = Field(ge=0, le=10)
    evidence: list[EvidenceSnippet] = Field(default_factory=list)


class GapDraft(BaseModel):
    gap_cards: list[GapDraftCard] = Field(default_factory=list)
    recommended_gap_title: str | None = None


class StudyPlanDraft(BaseModel):
    research_question: str
    boundary: str
    data_source: str
    metrics: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    validation: str


class MeetingDraft(BaseModel):
    decisions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    todos: list[str] = Field(default_factory=list)
    next_step: str


@dataclass
class ResearchInvestigationResult:
    research_state: ProjectState
    artifacts: ArtifactBundle
    workflow_steps: list[WorkflowStep]
    agent_tasks: list[AgentTask]
    stage: str
    knowledge_sources: list[KnowledgeSource]


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("JSON object not found in model response")
    return json.loads(cleaned[start : end + 1])


async def _call_openrouter_json(
    settings: Settings,
    *,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    if not settings.openrouter_ready or not settings.openrouter_api_key or not settings.openrouter_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenRouter is not fully configured",
        )

    candidate_models = [settings.openrouter_model]
    aliased_model = MODEL_ALIASES.get(settings.openrouter_model)
    if aliased_model and aliased_model not in candidate_models:
        candidate_models.append(aliased_model)
    for fallback in FREE_MODEL_FALLBACKS:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "GuideClaw",
    }

    response: httpx.Response | None = None
    async with httpx.AsyncClient(timeout=90) as client:
        for candidate in candidate_models:
            payload["model"] = candidate
            response = await client.post(
                f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            if response.status_code >= 400 and payload.get("response_format") is not None:
                fallback_payload = dict(payload)
                fallback_payload.pop("response_format", None)
                fallback_payload["messages"] = [
                    {"role": "system", "content": f"{system_prompt}\n\n你必须只输出一个 JSON 对象。"},
                    {"role": "user", "content": user_prompt},
                ]
                response = await client.post(
                    f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=fallback_payload,
                )
            if response.status_code in {402, 404, 429} and candidate != candidate_models[-1]:
                continue
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
    try:
        return _extract_json_object(content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": "OpenRouter returned invalid JSON", "body": content},
        ) from exc


def _rebuild_abstract(abstract_index: dict[str, list[int]] | None) -> str:
    if not abstract_index:
        return ""
    max_pos = max((max(positions) for positions in abstract_index.values() if positions), default=-1)
    if max_pos < 0:
        return ""
    tokens = [""] * (max_pos + 1)
    for word, positions in abstract_index.items():
        for position in positions:
            if 0 <= position < len(tokens):
                tokens[position] = word
    return " ".join(token for token in tokens if token).strip()


async def _search_openalex_works(query: str, per_page: int = 4) -> list[dict[str, str]]:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{OPENALEX_BASE_URL}/works",
                params={"search": query, "per-page": per_page},
                headers={"User-Agent": "GuideClaw/0.1"},
            )
        response.raise_for_status()
    except httpx.HTTPError:
        return []
    items = response.json().get("results", [])
    works: list[dict[str, str]] = []
    for item in items:
        title = item.get("display_name") or "未命名论文"
        year = str(item.get("publication_year") or "")
        abstract = _rebuild_abstract(item.get("abstract_inverted_index"))
        source = (((item.get("primary_location") or {}).get("source")) or {}).get("display_name") or "OpenAlex"
        doi = item.get("doi") or ""
        url = (
            ((item.get("primary_location") or {}).get("landing_page_url"))
            or ((item.get("primary_location") or {}).get("pdf_url"))
            or item.get("id")
            or ""
        )
        works.append(
            {
                "provider": "openalex",
                "source_type": "openalex",
                "external_id": item.get("id") or doi or url or title,
                "title": title,
                "year": year,
                "abstract": abstract,
                "source": source,
                "doi": doi,
                "url": url,
            }
        )
    return works


async def _search_research_sources(settings: Settings, query: str) -> list[dict[str, str]]:
    bohrium_works = await search_bohrium_papers(settings, query)
    if bohrium_works:
        return bohrium_works
    return await _search_openalex_works(query)


def _format_source_context(works: list[dict[str, str]]) -> str:
    if not works:
        return "- 暂无外部候选文献，必须显式说明证据不足。"
    lines = []
    for work in works:
        lines.append(
            f"- {work['title']}｜年份：{work['year'] or '未知'}｜来源：{work['source']}｜提供方：{work.get('provider') or '未知'}｜DOI：{work['doi'] or '无'}｜链接：{work['url'] or '无'}｜摘要：{work['abstract'] or '无摘要'}"
        )
    return "\n".join(lines)


def _build_citation(work: dict[str, str]) -> str:
    title = work.get("title") or "未命名论文"
    year = work.get("year") or "n.d."
    source = work.get("source") or "OpenAlex"
    doi = work.get("doi") or ""
    suffix = f" DOI: {doi}" if doi else ""
    return f"{title} ({year}). {source}.{suffix}".strip()


def _build_knowledge_sources(project_id: str, works: list[dict[str, str]]) -> list[KnowledgeSource]:
    sources: list[KnowledgeSource] = []
    seen_keys: set[str] = set()
    for work in works:
        unique_key = (work.get("doi") or work.get("url") or work.get("title") or "").strip()
        if not unique_key or unique_key in seen_keys:
            continue
        seen_keys.add(unique_key)
        sources.append(
            KnowledgeSource(
                id=f"src_{uuid4().hex[:10]}",
                project_id=project_id,
                source_type=work.get("source_type") or "skill_ingest",
                external_id=work.get("external_id") or work.get("url") or work.get("doi") or None,
                title=work.get("title") or "未命名论文",
                year=work.get("year") or None,
                venue=work.get("source") or None,
                doi=work.get("doi") or None,
                url=work.get("url") or None,
                abstract=work.get("abstract") or None,
                citation=_build_citation(work),
            )
        )
    return sources


def _chunks_for_source(source_id: str, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
    return [chunk for chunk in chunks if chunk.source_id == source_id]


def _evidence_from_hit(hit: Any) -> EvidenceSnippet:
    return EvidenceSnippet(
        source=hit.title,
        source_id=hit.source_id,
        chunk_id=getattr(hit, "chunk_id", None),
        source_type=hit.source_type,
        page=hit.page_from,
        page_to=hit.page_to,
        snippet=hit.excerpt,
        citation=hit.citation,
        doi=hit.doi,
        url=hit.url,
    )


def _fallback_evidence_from_source(source: KnowledgeSource, chunks: list[KnowledgeChunk]) -> list[EvidenceSnippet]:
    source_chunks = _chunks_for_source(source.id, chunks)
    if source_chunks:
        top_chunk = source_chunks[0]
        return [
            EvidenceSnippet(
                source=source.title,
                source_id=source.id,
                chunk_id=top_chunk.id,
                source_type=source.source_type,
                page=top_chunk.page_from,
                page_to=top_chunk.page_to,
                snippet=top_chunk.content[:420],
                citation=source.citation,
                doi=source.doi,
                url=source.url,
            )
        ]
    return [
        EvidenceSnippet(
            source=source.title,
            source_id=source.id,
            source_type=source.source_type,
            page=None,
            snippet=(source.abstract or source.citation or source.title)[:420],
            citation=source.citation,
            doi=source.doi,
            url=source.url,
        )
    ]


def _evidence_key(evidence: EvidenceSnippet) -> tuple[str, str, str, int, int, str]:
    return (
        evidence.source_id or "",
        evidence.chunk_id or "",
        evidence.url or "",
        evidence.page or 0,
        evidence.page_to or 0,
        evidence.snippet[:120],
    )


def _dedupe_evidence(evidence_list: list[EvidenceSnippet]) -> list[EvidenceSnippet]:
    seen: set[tuple[str, str, str, int, int, str]] = set()
    deduped: list[EvidenceSnippet] = []
    for evidence in evidence_list:
        key = _evidence_key(evidence)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(evidence)
    return deduped


def _evidence_from_sources(sources: list[KnowledgeSource], chunks: list[KnowledgeChunk], limit: int = 3) -> list[EvidenceSnippet]:
    evidence: list[EvidenceSnippet] = []
    for source in sources:
        evidence.extend(_fallback_evidence_from_source(source, chunks))
        if len(evidence) >= limit:
            break
    return _dedupe_evidence(evidence)[:limit]


def _flatten_evidence_pool(*groups: list[EvidenceSnippet]) -> list[EvidenceSnippet]:
    flattened: list[EvidenceSnippet] = []
    for group in groups:
        flattened.extend(group)
    return _dedupe_evidence(flattened)


def _knowledge_source_to_work(source: KnowledgeSource) -> dict[str, str]:
    return {
        "provider": "project_knowledge",
        "source_type": source.source_type,
        "external_id": source.external_id or source.id,
        "title": source.title,
        "year": source.year or "",
        "abstract": source.abstract or "",
        "source": source.venue or "项目知识库",
        "doi": source.doi or "",
        "url": source.url or "",
    }


def _dedupe_knowledge_sources(sources: list[KnowledgeSource]) -> list[KnowledgeSource]:
    deduped: list[KnowledgeSource] = []
    seen: set[tuple[str, str, str]] = set()
    for source in sources:
        key = (
            (source.doi or "").strip().lower(),
            (source.url or "").strip().lower(),
            source.title.strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped


def _format_project_knowledge_context(
    project_sources: list[KnowledgeSource],
    project_chunks: list[KnowledgeChunk],
    query: str,
) -> str:
    if not project_sources:
        return "- 当前项目知识库为空。"

    hits = search_project_knowledge(project_sources, project_chunks, query, limit=6)
    if hits:
        lines = []
        for hit in hits:
            page_text = ""
            if hit.page_from:
                page_text = f"｜页码：{hit.page_from}"
                if hit.page_to and hit.page_to != hit.page_from:
                    page_text = f"｜页码：{hit.page_from}-{hit.page_to}"
            lines.append(
                f"- {hit.title}｜类型：{hit.source_type}{page_text}｜引用：{hit.citation or '暂无'}｜DOI：{hit.doi or '无'}｜链接：{hit.url or '无'}｜片段：{hit.excerpt}"
            )
        return "\n".join(lines)

    fallback_lines = []
    for source in project_sources[:5]:
        fallback_lines.append(
            f"- {source.title}｜类型：{source.source_type}｜引用：{source.citation or '暂无'}｜DOI：{source.doi or '无'}｜链接：{source.url or '无'}｜摘要：{source.abstract or '暂无摘要'}"
        )
    return "\n".join(fallback_lines)


def _build_agent_tasks(
    project: Project,
    research_focus: str,
    key_questions: list[str],
    recommended_gap: str,
    next_step: str,
    knowledge_sources: list[KnowledgeSource],
    artifacts: ArtifactBundle,
) -> list[AgentTask]:
    source_ids = [source.id for source in knowledge_sources]
    literature_ids = [card.id for card in artifacts.literature_cards]
    gap_ids = [card.id for card in artifacts.gap_cards]
    plan_ids = [card.id for card in artifacts.plan_cards]
    meeting_ids = [card.id for card in artifacts.meeting_notes]

    pi_task_id = f"task_{uuid4().hex[:10]}"
    literature_task_id = f"task_{uuid4().hex[:10]}"
    gap_task_id = f"task_{uuid4().hex[:10]}"
    plan_task_id = f"task_{uuid4().hex[:10]}"
    meeting_task_id = f"task_{uuid4().hex[:10]}"

    return [
        AgentTask(
            id=pi_task_id,
            project_id=project.id,
            role="principal_investigator",
            title="PI 收敛首轮调查目标",
            objective=f"围绕“{research_focus}”界定本轮研究边界，并把问题拆成可执行任务。",
            status="completed",
            inputs=[project.title, project.summary or "暂无补充说明"],
            expected_output="一份包含研究焦点、关键问题和检索词的任务分发单。",
            output_summary=f"已确定首轮聚焦：{research_focus}；关键问题 {len(key_questions)} 个。",
        ),
        AgentTask(
            id=literature_task_id,
            project_id=project.id,
            role="literature_assistant",
            title="文献助理建立领域地图",
            objective="检索候选论文，整理代表工作、方法路径、数据来源与证据链接。",
            status="completed",
            inputs=key_questions or [project.title],
            expected_output="2-3 张文献卡，每张都绑定可打开的来源链接和引用信息。",
            output_summary=f"已沉淀 {len(literature_ids)} 张文献卡，候选来源 {len(source_ids)} 条。",
            depends_on=[pi_task_id],
            evidence_source_ids=source_ids,
            artifact_ids=literature_ids,
        ),
        AgentTask(
            id=gap_task_id,
            project_id=project.id,
            role="gap_analyst",
            title="选题分析员筛选优先缺口",
            objective="基于现有文献卡，比较新颖性、重要性和可行性，选出最值得推进的一项。",
            status="completed",
            inputs=["文献卡", "知识源列表"],
            expected_output="候选缺口排序和一个明确的优先缺口。",
            output_summary=f"已从候选缺口中收敛出优先项：{recommended_gap or '待补充'}。",
            depends_on=[literature_task_id],
            evidence_source_ids=source_ids,
            artifact_ids=gap_ids,
        ),
        AgentTask(
            id=plan_task_id,
            project_id=project.id,
            role="study_designer",
            title="方案设计师生成最小可行方案",
            objective="把优先缺口转成可讨论、可执行、可验证的首轮研究方案。",
            status="completed",
            inputs=[recommended_gap or "暂无明确缺口", "缺口卡"],
            expected_output="1 张方案卡，说明边界、数据、指标、方法和验证路径。",
            output_summary="已生成首轮研究方案，可直接进入导师/组会讨论。",
            depends_on=[gap_task_id],
            evidence_source_ids=source_ids,
            artifact_ids=plan_ids,
        ),
        AgentTask(
            id=meeting_task_id,
            project_id=project.id,
            role="meeting_secretary",
            title="组会秘书沉淀行动项",
            objective="把本轮调查的结论、待办与下一步推进顺序固化下来。",
            status="completed",
            inputs=["方案卡", "缺口卡", "文献卡"],
            expected_output="1 张纪要卡，包含决策、开放问题、待办和 next step。",
            output_summary=next_step or "已完成本轮纪要沉淀。",
            depends_on=[plan_task_id],
            evidence_source_ids=source_ids,
            artifact_ids=meeting_ids,
        ),
    ]


def _match_work_to_title(title: str, works: list[dict[str, str]]) -> dict[str, str] | None:
    normalized = title.strip().lower()
    best_match: dict[str, str] | None = None
    best_score = 0.0
    for work in works:
        candidate = (work.get("title") or "").strip().lower()
        if not candidate:
            continue
        if normalized and (normalized in candidate or candidate in normalized):
            return work
        score = SequenceMatcher(None, normalized, candidate).ratio()
        if score > best_score:
            best_score = score
            best_match = work
    if best_score >= 0.45:
        return best_match
    return works[0] if works else None


def _ground_literature_evidence(
    cards: list[LiteratureDraftCard],
    works: list[dict[str, str]],
    project_sources: list[KnowledgeSource],
    project_chunks: list[KnowledgeChunk],
) -> list[LiteratureDraftCard]:
    source_map = {source.id: source for source in project_sources}
    grounded_cards: list[LiteratureDraftCard] = []
    for card in cards:
        matched_work = _match_work_to_title(card.title, works)
        if matched_work is None:
            grounded_cards.append(card)
            continue
        matched_source = next(
            (
                source
                for source in project_sources
                if (source.doi and source.doi == matched_work.get("doi"))
                or (source.url and source.url == matched_work.get("url"))
                or source.title.strip().lower() == (matched_work.get("title") or "").strip().lower()
            ),
            None,
        )
        evidence: list[EvidenceSnippet] = []
        if matched_source is not None:
            scoped_hits = search_project_knowledge(
                [matched_source],
                _chunks_for_source(matched_source.id, project_chunks),
                " ".join(
                    part
                    for part in [card.title, card.research_question, card.method]
                    if part
                ),
                limit=2,
            )
            evidence = [_evidence_from_hit(hit) for hit in scoped_hits]
            if not evidence:
                evidence = _fallback_evidence_from_source(matched_source, project_chunks)
        elif matched_work.get("external_id") in source_map:
            fallback_source = source_map[matched_work["external_id"]]
            evidence = _fallback_evidence_from_source(fallback_source, project_chunks)
        else:
            evidence = [
                EvidenceSnippet(
                    source=f"{matched_work['title']}｜{matched_work['source']}",
                    page=None,
                    snippet=matched_work.get("abstract")
                    or f"{matched_work.get('provider') or '外部检索'} 元数据显示：{matched_work['title']}，发表年份 {matched_work.get('year') or '未知'}。",
                    citation=_build_citation(matched_work),
                    doi=matched_work.get("doi") or None,
                    url=matched_work.get("url") or None,
                )
            ]
        grounded_cards.append(
            card.model_copy(
                update={
                    "evidence": evidence
                }
            )
        )
    return grounded_cards


def _ground_gap_evidence(
    cards: list[GapDraftCard],
    project_sources: list[KnowledgeSource],
    project_chunks: list[KnowledgeChunk],
    *,
    fallback_evidence_pool: list[EvidenceSnippet] | None = None,
) -> list[GapDraftCard]:
    grounded_cards: list[GapDraftCard] = []
    fallback_evidence_pool = fallback_evidence_pool or []
    for card in cards:
        hits = search_project_knowledge(
            project_sources,
            project_chunks,
            " ".join(part for part in [card.title, card.why_it_matters] if part),
            limit=2,
        )
        evidence = _dedupe_evidence([_evidence_from_hit(hit) for hit in hits])
        if not evidence:
            evidence = _dedupe_evidence([*card.evidence, *fallback_evidence_pool[:2]])
        if not evidence:
            evidence = _evidence_from_sources(project_sources, project_chunks, limit=2)
        grounded_cards.append(card.model_copy(update={"evidence": evidence}))
    return grounded_cards


def _build_plan_evidence(
    project_sources: list[KnowledgeSource],
    project_chunks: list[KnowledgeChunk],
    *,
    research_question: str,
    boundary: str,
    fallback_evidence_pool: list[EvidenceSnippet] | None = None,
) -> list[EvidenceSnippet]:
    hits = search_project_knowledge(
        project_sources,
        project_chunks,
        " ".join(part for part in [research_question, boundary] if part),
        limit=3,
    )
    evidence = _dedupe_evidence([_evidence_from_hit(hit) for hit in hits])
    if evidence:
        return evidence[:3]
    if fallback_evidence_pool:
        return _dedupe_evidence(fallback_evidence_pool)[:3]
    return _evidence_from_sources(project_sources, project_chunks, limit=3)


def _build_meeting_evidence(
    project_sources: list[KnowledgeSource],
    project_chunks: list[KnowledgeChunk],
    *,
    next_step: str,
    decisions: list[str],
    fallback_evidence_pool: list[EvidenceSnippet] | None = None,
) -> list[EvidenceSnippet]:
    hits = search_project_knowledge(
        project_sources,
        project_chunks,
        " ".join([*decisions[:2], next_step]),
        limit=2,
    )
    evidence = _dedupe_evidence([_evidence_from_hit(hit) for hit in hits])
    if evidence:
        return evidence[:3]
    if fallback_evidence_pool:
        return _dedupe_evidence(fallback_evidence_pool)[:3]
    return _evidence_from_sources(project_sources, project_chunks, limit=2)


async def bootstrap_research_workflow(
    settings: Settings,
    project: Project,
    *,
    existing_sources: list[KnowledgeSource] | None = None,
    existing_chunks: list[KnowledgeChunk] | None = None,
) -> ResearchInvestigationResult:
    existing_sources = existing_sources or []
    existing_chunks = existing_chunks or []
    project_knowledge_context = _format_project_knowledge_context(
        existing_sources,
        existing_chunks,
        f"{project.title}\n{project.summary or ''}",
    )

    pi_json = await _call_openrouter_json(
        settings,
        system_prompt=(
            "你是引路虾里的课题负责人。你负责把用户给定的研究题目收敛成第一轮调查计划。"
            "你必须输出 JSON，不要输出额外说明。"
            "JSON 字段：current_stage, research_focus, why_now, key_questions, search_queries。"
            "search_queries 只给 2-4 个最有代表性的英文或中英混合检索词。"
        ),
        user_prompt=dedent(
            f"""
            研究题目：{project.title}
            相关说明：{project.summary or '暂无补充说明'}
            项目知识库现状：
            {project_knowledge_context}

            请给出首轮调查的聚焦点、为什么值得调查、关键问题，以及适合去文献检索引擎检索的关键词。
            """
        ).strip(),
    )
    pi_json["current_stage"] = _normalize_stage(pi_json.get("current_stage"))
    pi_draft = PrincipalInvestigatorDraft.model_validate(pi_json)

    literature_query = " OR ".join(pi_draft.search_queries[:3]) or project.title
    works = await _search_research_sources(settings, literature_query)
    knowledge_sources = _build_knowledge_sources(project.id, works)
    all_context_sources = _dedupe_knowledge_sources([*existing_sources, *knowledge_sources])
    generated_chunks = []
    for source in knowledge_sources:
        generated_chunks.extend(build_source_chunks(source))
    all_context_chunks = [*existing_chunks, *generated_chunks]
    all_reference_works = [_knowledge_source_to_work(source) for source in all_context_sources]
    source_context = _format_source_context(works)
    project_knowledge_context = _format_project_knowledge_context(
        existing_sources,
        existing_chunks,
        " ".join([project.title, *pi_draft.search_queries[:2], *pi_draft.key_questions[:2]]),
    )

    literature_json = await _call_openrouter_json(
        settings,
        system_prompt=(
            "你是引路虾里的文献助理。你只能基于用户提供的项目说明和候选文献信息生成文献卡。"
            "不要编造论文，不要补不存在的实验结果。若证据不足，必须把限制写清楚。"
            "输出 JSON，字段为 literature_cards，每张卡包含：title, research_question, method, data_source, "
            "key_result, limitations, evidence。evidence 每项包含 source, page, snippet, citation, doi, url。"
            "evidence.snippet 必须尽量直接引用候选文献元数据或摘要，不要编造。page 没有就填 null。"
        ),
        user_prompt=dedent(
            f"""
            项目标题：{project.title}
            项目说明：{project.summary or '暂无'}
            课题负责人聚焦：{pi_draft.research_focus}
            关键问题：{'; '.join(pi_draft.key_questions) or '暂无'}
            项目知识库命中：
            {project_knowledge_context}

            候选文献信息：
            {source_context}

            请生成 2-3 张真实、克制、带限制说明的文献卡。
            """
        ).strip(),
    )
    for card in literature_json.get("literature_cards", []):
        card["limitations"] = _ensure_str_list(card.get("limitations"))
        card["evidence"] = _sanitize_evidence(card.get("evidence"))
    literature_draft = LiteratureDraft.model_validate(literature_json)
    literature_cards = _ground_literature_evidence(
        literature_draft.literature_cards,
        all_reference_works,
        all_context_sources,
        all_context_chunks,
    )
    literature_draft = literature_draft.model_copy(update={"literature_cards": literature_cards})
    literature_evidence_pool = _flatten_evidence_pool(
        *[card.evidence for card in literature_draft.literature_cards]
    )

    literature_context = json.dumps(literature_draft.model_dump(), ensure_ascii=False, indent=2)

    gap_json = await _call_openrouter_json(
        settings,
        system_prompt=(
            "你是引路虾里的选题分析员。你要基于已有文献卡，找出真正值得优先推进的研究缺口。"
            "不要追求列很多条，宁可少而准。输出 JSON，字段为 gap_cards 和 recommended_gap_title。"
            "gap_cards 每项包含：title, gap_type, why_it_matters, novelty_score, importance_score, feasibility_score, evidence。"
        ),
        user_prompt=dedent(
            f"""
            项目标题：{project.title}
            项目说明：{project.summary or '暂无'}
            文献卡：
            {literature_context}
            已有知识库命中：
            {project_knowledge_context}

            请输出 2 张研究缺口卡，并指出最值得优先推进的一项。
            """
        ).strip(),
    )
    for card in gap_json.get("gap_cards", []):
        card["novelty_score"] = _normalize_score(card.get("novelty_score"))
        card["importance_score"] = _normalize_score(card.get("importance_score"))
        card["feasibility_score"] = _normalize_score(card.get("feasibility_score"))
        card["evidence"] = _sanitize_evidence(card.get("evidence"))
    gap_draft = GapDraft.model_validate(gap_json)
    gap_cards_grounded = _ground_gap_evidence(
        gap_draft.gap_cards,
        all_context_sources,
        all_context_chunks,
        fallback_evidence_pool=literature_evidence_pool,
    )
    gap_draft = gap_draft.model_copy(update={"gap_cards": gap_cards_grounded})
    gap_evidence_pool = _flatten_evidence_pool(*[card.evidence for card in gap_draft.gap_cards])

    recommended_gap = gap_draft.recommended_gap_title or (gap_draft.gap_cards[0].title if gap_draft.gap_cards else "")
    gap_context = json.dumps(gap_draft.model_dump(), ensure_ascii=False, indent=2)

    plan_json = await _call_openrouter_json(
        settings,
        system_prompt=(
            "你是引路虾里的方案设计师。你要把优先缺口收敛成一版可以直接拿去讨论的研究方案。"
            "输出 JSON，字段：research_question, boundary, data_source, metrics, methods, validation。"
            "强调最小可行方案，不要写宏大叙事。"
        ),
        user_prompt=dedent(
            f"""
            项目标题：{project.title}
            项目说明：{project.summary or '暂无'}
            优先缺口：{recommended_gap or '暂无明确缺口'}
            缺口信息：
            {gap_context}
            已有知识库命中：
            {project_knowledge_context}

            请输出一版适合科研新人的首轮研究方案。
            """
        ).strip(),
    )
    plan_json["metrics"] = _ensure_str_list(plan_json.get("metrics"))
    plan_json["methods"] = _ensure_str_list(plan_json.get("methods"))
    plan_json["research_question"] = _ensure_single_text(plan_json.get("research_question"))
    plan_json["boundary"] = _ensure_single_text(plan_json.get("boundary"))
    plan_json["data_source"] = _ensure_single_text(plan_json.get("data_source"))
    plan_json["validation"] = _ensure_single_text(plan_json.get("validation"))
    plan_draft = StudyPlanDraft.model_validate(plan_json)
    plan_evidence = _build_plan_evidence(
        all_context_sources,
        all_context_chunks,
        research_question=plan_draft.research_question,
        boundary=plan_draft.boundary,
        fallback_evidence_pool=_flatten_evidence_pool(literature_evidence_pool, gap_evidence_pool),
    )

    plan_context = json.dumps(plan_draft.model_dump(), ensure_ascii=False, indent=2)
    meeting_json = await _call_openrouter_json(
        settings,
        system_prompt=(
            "你是引路虾里的组会秘书。你要把本轮调查的关键信息收口成结论、未解决问题和待办。"
            "输出 JSON，字段：decisions, open_questions, todos, next_step。"
        ),
        user_prompt=dedent(
            f"""
            项目标题：{project.title}
            项目说明：{project.summary or '暂无'}
            课题负责人：
            {json.dumps(pi_draft.model_dump(), ensure_ascii=False, indent=2)}

            文献卡：
            {literature_context}

            缺口卡：
            {gap_context}

            方案卡：
            {plan_context}

            请生成一份适合下一次讨论的纪要与行动项。
            """
        ).strip(),
    )
    meeting_json["decisions"] = _ensure_str_list(meeting_json.get("decisions"))
    meeting_json["open_questions"] = _ensure_str_list(meeting_json.get("open_questions"))
    meeting_json["todos"] = _ensure_str_list(meeting_json.get("todos"))
    meeting_json["next_step"] = _ensure_single_text(meeting_json.get("next_step"))
    meeting_draft = MeetingDraft.model_validate(meeting_json)
    meeting_evidence = _build_meeting_evidence(
        all_context_sources,
        all_context_chunks,
        next_step=meeting_draft.next_step,
        decisions=meeting_draft.decisions,
        fallback_evidence_pool=_flatten_evidence_pool(literature_evidence_pool, gap_evidence_pool, plan_evidence),
    )

    artifacts = ArtifactBundle(
        literature_cards=[
            LiteratureCard(
                id=f"lit_{uuid4().hex[:10]}",
                project_id=project.id,
                title=card.title,
                research_question=card.research_question,
                method=card.method,
                data_source=card.data_source,
                key_result=card.key_result,
                limitations=card.limitations,
                evidence=card.evidence,
            )
            for card in literature_draft.literature_cards
        ],
        gap_cards=[
            GapCard(
                id=f"gap_{uuid4().hex[:10]}",
                project_id=project.id,
                title=card.title,
                gap_type=card.gap_type,
                why_it_matters=card.why_it_matters,
                novelty_score=card.novelty_score,
                importance_score=card.importance_score,
                feasibility_score=card.feasibility_score,
                evidence=card.evidence,
            )
            for card in gap_draft.gap_cards
        ],
        plan_cards=[
            PlanCard(
                id=f"plan_{uuid4().hex[:10]}",
                project_id=project.id,
                research_question=plan_draft.research_question,
                boundary=plan_draft.boundary,
                data_source=plan_draft.data_source,
                metrics=plan_draft.metrics,
                methods=plan_draft.methods,
                validation=plan_draft.validation,
                evidence=plan_evidence,
            )
        ],
        meeting_notes=[
            MeetingNote(
                id=f"note_{uuid4().hex[:10]}",
                project_id=project.id,
                decisions=meeting_draft.decisions,
                open_questions=meeting_draft.open_questions,
                todos=meeting_draft.todos,
                next_step=meeting_draft.next_step,
                evidence=meeting_evidence,
            )
        ],
    )

    workflow_steps = [
        WorkflowStep(
            role="principal_investigator",
            title="课题负责人定焦",
            summary=f"聚焦 {pi_draft.research_focus}，优先回答：{('；'.join(pi_draft.key_questions[:2]) or '研究切入点与推进顺序')}。",
        ),
        WorkflowStep(
            role="literature_assistant",
            title="文献助理建立领域地图",
            summary=f"围绕 {len(artifacts.literature_cards)} 条候选文献线索整理了第一轮文献卡，数据源优先使用 {'Bohrium' if works and works[0].get('provider') == 'bohrium' else 'OpenAlex'}。",
        ),
        WorkflowStep(
            role="gap_analyst",
            title="选题分析员筛缺口",
            summary=f"从 {len(artifacts.gap_cards)} 个候选缺口里收敛到优先项：{recommended_gap or '待进一步判断'}。",
        ),
        WorkflowStep(
            role="study_designer",
            title="方案设计师收成研究方案",
            summary=plan_draft.research_question,
        ),
        WorkflowStep(
            role="meeting_secretary",
            title="组会秘书沉淀行动项",
            summary=meeting_draft.next_step,
        ),
    ]

    literature_provider = works[0].get("provider") if works else None
    provider_label = {
        "bohrium": "Bohrium 文献技能",
        "openalex": "OpenAlex 回退检索",
    }.get(literature_provider or "", "暂无外部检索结果")
    local_knowledge_note = (
        f"项目知识库已接入 {len(existing_sources)} 条本地来源"
        if existing_sources
        else "当前没有用户上传或手工沉淀的本地知识源"
    )

    research_state = ProjectState(
        project_id=project.id,
        research_focus=pi_draft.research_focus,
        why_now=pi_draft.why_now,
        key_questions=pi_draft.key_questions,
        search_queries=pi_draft.search_queries,
        recommended_gap_title=recommended_gap or None,
        current_hypothesis=plan_draft.research_question,
        next_step=meeting_draft.next_step,
        literature_provider=literature_provider,
        provider_note=f"当前文献检索主来源：{provider_label}；{local_knowledge_note}",
        last_investigated_at=utc_now(),
    )
    agent_tasks = _build_agent_tasks(
        project=project,
        research_focus=pi_draft.research_focus,
        key_questions=pi_draft.key_questions,
        recommended_gap=recommended_gap,
        next_step=meeting_draft.next_step,
        knowledge_sources=all_context_sources,
        artifacts=artifacts,
    )

    return ResearchInvestigationResult(
        research_state=research_state,
        artifacts=artifacts,
        workflow_steps=workflow_steps,
        agent_tasks=agent_tasks,
        stage="proposal",
        knowledge_sources=knowledge_sources,
    )
