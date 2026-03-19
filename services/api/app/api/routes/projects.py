from __future__ import annotations

import asyncio
import json
from pathlib import Path
from textwrap import dedent
from typing import Literal
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from app.domain.schemas import (
    AgentTask,
    AgentRunRequest,
    AgentRunResponse,
    ArtifactBundle,
    FollowUpDelegate,
    FollowUpDelegateResult,
    FollowUpRequest,
    FollowUpResponse,
    GeneratedDocument,
    InvestigationResponse,
    KnowledgeHit,
    KnowledgeSource,
    LlmSummaryResponse,
    PdfUploadResponse,
    Project,
    ProjectCreate,
    ProjectState,
    ResultSummaryResponse,
    ProjectWorkspace,
    TranslateRequest,
    TranslateResponse,
    WorkflowStep,
)
from app.services.knowledge_ingest import build_source_chunks, ingest_pdf
from app.services.knowledge_search import search_project_knowledge
from app.services.openclaw_client import run_openclaw_role
from app.services.research_workflow import bootstrap_research_workflow
from app.services.result_summary import (
    build_result_summary,
    build_result_summary_markdown,
    build_result_summary_pdf,
)
from app.settings import get_settings
from app.services.openrouter_client import generate_project_summary, plan_follow_up, translate_text
from app.store import SQLiteProjectStore

router = APIRouter(prefix="/projects", tags=["projects"])
settings = get_settings()
store = SQLiteProjectStore(settings.guideclaw_database_path)


def _render_investigation_markdown(
    project: Project,
    state: ProjectState,
    artifacts: ArtifactBundle,
    workflow_steps: list[WorkflowStep],
    knowledge_sources: list[KnowledgeSource],
) -> str:
    literature_lines = [
        f"- **{card.title}**：{card.research_question}；关键结论：{card.key_result}"
        for card in artifacts.literature_cards[:3]
    ] or ["- 当前还没有文献卡。"]
    gap_lines = [
        f"- **{card.title}**｜重要性 {card.importance_score}/10｜可行性 {card.feasibility_score}/10"
        for card in artifacts.gap_cards[:3]
    ] or ["- 当前还没有缺口卡。"]
    plan = artifacts.plan_cards[0] if artifacts.plan_cards else None
    meeting = artifacts.meeting_notes[0] if artifacts.meeting_notes else None
    workflow_lines = [
        f"{index + 1}. **{step.title}**：{step.summary}"
        for index, step in enumerate(workflow_steps)
    ] or ["1. 当前还没有工作流步骤。"]
    source_lines = [
        f"- [{source.title}]({source.url})"
        if source.url
        else f"- {source.title}"
        for source in knowledge_sources[:5]
    ] or ["- 当前还没有知识源。"]

    return "\n".join(
        [
            f"# {project.title}",
            "",
            "## 本轮聚焦",
            state.research_focus or "尚未定义",
            "",
            "## 为什么值得现在做",
            state.why_now or "尚未补充",
            "",
            "## 关键问题",
            *([f"- {item}" for item in state.key_questions] or ["- 当前还没有关键问题。"]),
            "",
            "## 文献地图",
            *literature_lines,
            "",
            "## 优先缺口",
            *gap_lines,
            "",
            "## 首轮方案",
            f"- 研究问题：{plan.research_question}" if plan else "- 当前还没有方案卡。",
            f"- 研究边界：{plan.boundary}" if plan else "",
            f"- 数据来源：{plan.data_source}" if plan else "",
            f"- 方法：{'、'.join(plan.methods)}" if plan else "",
            "",
            "## 纪要与下一步",
            *( [f"- {item}" for item in meeting.decisions[:3]] if meeting else ["- 当前还没有纪要。"] ),
            f"- 下一步：{meeting.next_step}" if meeting else "",
            "",
            "## PI 编排链路",
            *workflow_lines,
            "",
            "## 当前知识源",
            *source_lines,
        ]
    ).strip()


def _dedupe_evidence_items(items: list) -> list:
    deduped = []
    seen = set()
    for item in items:
        key = (
            getattr(item, "source_id", None) or "",
            getattr(item, "chunk_id", None) or "",
            getattr(item, "url", None) or "",
            getattr(item, "page", None) or 0,
            getattr(item, "page_to", None) or 0,
            (getattr(item, "snippet", None) or "")[:120],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _backfill_artifact_evidence(artifacts: ArtifactBundle) -> ArtifactBundle:
    literature_pool = _dedupe_evidence_items(
        [item for card in artifacts.literature_cards for item in card.evidence]
    )
    gap_cards = []
    for card in artifacts.gap_cards:
        evidence = card.evidence or literature_pool[:2]
        gap_cards.append(card.model_copy(update={"evidence": _dedupe_evidence_items(evidence)[:2]}))
    gap_pool = _dedupe_evidence_items([item for card in gap_cards for item in card.evidence])

    plan_cards = []
    for card in artifacts.plan_cards:
        evidence = card.evidence or _dedupe_evidence_items([*gap_pool[:2], *literature_pool[:2]])
        plan_cards.append(card.model_copy(update={"evidence": _dedupe_evidence_items(evidence)[:3]}))
    plan_pool = _dedupe_evidence_items([item for card in plan_cards for item in card.evidence])

    meeting_notes = []
    for card in artifacts.meeting_notes:
        evidence = card.evidence or _dedupe_evidence_items([*plan_pool[:2], *gap_pool[:2], *literature_pool[:1]])
        meeting_notes.append(card.model_copy(update={"evidence": _dedupe_evidence_items(evidence)[:3]}))

    return artifacts.model_copy(
        update={
            "gap_cards": gap_cards,
            "plan_cards": plan_cards,
            "meeting_notes": meeting_notes,
        }
    )


@router.get("", response_model=list[Project])
async def list_projects() -> list[Project]:
    return store.list_projects()


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate) -> Project:
    return store.create_project(payload)


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str) -> Project:
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return project


@router.get("/{project_id}/workspace", response_model=ProjectWorkspace)
async def get_project_workspace(project_id: str) -> ProjectWorkspace:
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    research_state = store.get_state(project_id) or ProjectState(project_id=project_id)
    artifacts = store.get_artifacts(project_id) or ArtifactBundle()
    workflow_steps = store.get_workflow_steps(project_id) or []
    agent_tasks = store.list_agent_tasks(project_id) or []
    knowledge_sources = store.list_knowledge_sources(project_id) or []
    repaired_artifacts = _backfill_artifact_evidence(artifacts)
    if repaired_artifacts != artifacts:
        artifacts = repaired_artifacts
        store.update_research_outputs(
            project_id,
            stage=project.stage,
            state=research_state,
            artifacts=artifacts,
            workflow_steps=workflow_steps,
            agent_tasks=agent_tasks,
        )
    generated_documents = store.list_generated_documents(project_id) or []
    return ProjectWorkspace(
        project=project,
        research_state=research_state,
        artifacts=artifacts,
        workflow_steps=workflow_steps,
        agent_tasks=agent_tasks,
        knowledge_sources=knowledge_sources,
        generated_documents=generated_documents,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str) -> Response:
    deleted = store.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/artifacts", response_model=ArtifactBundle)
async def get_project_artifacts(project_id: str) -> ArtifactBundle:
    artifacts = store.get_artifacts(project_id)
    if artifacts is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return artifacts


@router.get("/{project_id}/state", response_model=ProjectState)
async def get_project_state(project_id: str) -> ProjectState:
    project_state = store.get_state(project_id)
    if project_state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return project_state


@router.get("/{project_id}/workflow", response_model=list[WorkflowStep])
async def get_project_workflow(project_id: str) -> list[WorkflowStep]:
    workflow_steps = store.get_workflow_steps(project_id)
    if workflow_steps is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return workflow_steps


@router.get("/{project_id}/tasks", response_model=list[AgentTask])
async def get_project_agent_tasks(project_id: str) -> list[AgentTask]:
    agent_tasks = store.list_agent_tasks(project_id)
    if agent_tasks is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return agent_tasks


@router.get("/{project_id}/knowledge-sources", response_model=list[KnowledgeSource])
async def get_project_knowledge_sources(project_id: str) -> list[KnowledgeSource]:
    knowledge_sources = store.list_knowledge_sources(project_id)
    if knowledge_sources is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return knowledge_sources


@router.get("/{project_id}/documents", response_model=list[GeneratedDocument])
async def get_project_documents(project_id: str) -> list[GeneratedDocument]:
    documents = store.list_generated_documents(project_id)
    if documents is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return documents


@router.get("/{project_id}/result-summary", response_model=ResultSummaryResponse)
async def get_project_result_summary(project_id: str) -> ResultSummaryResponse:
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    state = store.get_state(project_id) or ProjectState(project_id=project_id)
    artifacts = _backfill_artifact_evidence(store.get_artifacts(project_id) or ArtifactBundle())
    knowledge_sources = store.list_knowledge_sources(project_id) or []
    generated_documents = store.list_generated_documents(project_id) or []
    summary = build_result_summary(
        settings,
        project=project,
        state=state,
        artifacts=artifacts,
        knowledge_sources=knowledge_sources,
        generated_documents=generated_documents,
    )
    store.save_generated_document(
        GeneratedDocument(
            id=f"doc_result_{project_id}",
            project_id=project_id,
            doc_type="result_summary",
            title="结果汇总",
            content=build_result_summary_markdown(summary),
            source="system",
        )
    )
    return summary


@router.get("/{project_id}/result-summary.pdf")
async def download_project_result_summary_pdf(project_id: str) -> Response:
    summary = await get_project_result_summary(project_id)
    pdf_bytes = build_result_summary_pdf(summary)
    filename = f"{project_id}-result-summary.pdf"
    quoted_filename = quote(f"{summary.project_title}-结果汇总.pdf")
    headers = {
        "Content-Disposition": f"inline; filename=\"{filename}\"; filename*=UTF-8''{quoted_filename}",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.get("/{project_id}/knowledge-search", response_model=list[KnowledgeHit])
async def search_project_knowledge_sources(project_id: str, q: str = "") -> list[KnowledgeHit]:
    knowledge_sources = store.list_knowledge_sources(project_id)
    knowledge_chunks = store.list_knowledge_chunks(project_id)
    if knowledge_sources is None or knowledge_chunks is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return search_project_knowledge(knowledge_sources, knowledge_chunks, q)


@router.post("/{project_id}/pdf-upload", response_model=PdfUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_pdf(project_id: str, file: UploadFile = File(...)) -> PdfUploadResponse:
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")

    filename = file.filename or "uploaded.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="only PDF files are supported")

    upload_dir = settings.guideclaw_upload_root / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in filename)
    file_path = upload_dir / f"{uuid4().hex[:8]}-{safe_name}"
    file_bytes = await file.read()
    file_path.write_bytes(file_bytes)

    source_id = f"src_{uuid4().hex[:10]}"
    preview, chunks = ingest_pdf(project_id, source_id, file_path)
    download_url = f"{settings.guideclaw_api_base_url.rstrip('/')}/projects/{project_id}/files/{source_id}"
    source = KnowledgeSource(
        id=source_id,
        project_id=project_id,
        source_type="pdf_upload",
        external_id=str(file_path),
        title=Path(filename).stem,
        venue="用户上传 PDF",
        url=download_url,
        abstract=preview or "已上传 PDF，等待进一步解析。",
        citation=f"{Path(filename).stem}. User uploaded PDF.",
    )
    store.add_knowledge_source(source)
    store.replace_source_chunks(source.id, chunks or build_source_chunks(source))
    return PdfUploadResponse(source=source, chunk_count=len(chunks))


@router.get("/{project_id}/files/{source_id}")
async def download_project_pdf(project_id: str, source_id: str) -> FileResponse:
    knowledge_sources = store.list_knowledge_sources(project_id)
    if knowledge_sources is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    matched = next((item for item in knowledge_sources if item.id == source_id and item.source_type == "pdf_upload"), None)
    if matched is None or not matched.external_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pdf source not found")
    file_path = Path(matched.external_id)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pdf file missing")
    return FileResponse(file_path, media_type="application/pdf", filename=file_path.name)


@router.post("/{project_id}/investigate", response_model=InvestigationResponse)
async def investigate_project(project_id: str) -> InvestigationResponse:
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")

    existing_sources = store.list_knowledge_sources(project_id) or []
    existing_chunks = store.list_knowledge_chunks(project_id) or []
    result = await bootstrap_research_workflow(
        settings,
        project,
        existing_sources=existing_sources,
        existing_chunks=existing_chunks,
    )
    updated_project = store.update_research_outputs(
        project_id,
        stage=result.stage,
        state=result.research_state,
        artifacts=result.artifacts,
        workflow_steps=result.workflow_steps,
        agent_tasks=result.agent_tasks,
    )
    store.replace_knowledge_sources(project_id, result.knowledge_sources)
    if updated_project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    for source in result.knowledge_sources:
        store.replace_source_chunks(source.id, build_source_chunks(source))
    store.save_generated_document(
        GeneratedDocument(
            id=f"doc_digest_{uuid4().hex[:10]}",
            project_id=project_id,
            doc_type="project_summary",
            title="首轮调查摘要",
            content=_render_investigation_markdown(
                updated_project,
                result.research_state,
                result.artifacts,
                result.workflow_steps,
                result.knowledge_sources,
            ),
            source="system",
        )
    )

    return InvestigationResponse(
        project=updated_project,
        research_state=result.research_state,
        artifacts=result.artifacts,
        workflow_steps=result.workflow_steps,
        agent_tasks=result.agent_tasks,
    )


@router.post("/{project_id}/llm-summary", response_model=LlmSummaryResponse)
async def create_project_llm_summary(project_id: str) -> LlmSummaryResponse:
    project = store.get_project(project_id)
    artifacts = store.get_artifacts(project_id)

    if project is None or artifacts is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")

    model, content = await generate_project_summary(settings, project, artifacts)
    store.save_generated_document(
        GeneratedDocument(
            id=f"doc_summary_{uuid4().hex[:10]}",
            project_id=project_id,
            doc_type="project_summary",
            title="研究摘要",
            content=content,
            source="minimax",
            model=model,
        )
    )
    return LlmSummaryResponse(project_id=project_id, model=model, content=content)


@router.post("/{project_id}/agent-run", response_model=AgentRunResponse)
async def create_project_agent_run(project_id: str, payload: AgentRunRequest) -> AgentRunResponse:
    project = store.get_project(project_id)

    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")

    result = await run_openclaw_role(settings, project_id, payload)
    store.save_generated_document(
        GeneratedDocument(
            id=f"doc_agent_{uuid4().hex[:10]}",
            project_id=project_id,
            doc_type="agent_run",
            title=ROLE_TITLE_MAP[payload.role],
            role=payload.role,
            content=result.content,
            source="openclaw",
            model=result.model,
            session_id=result.session_id,
        )
    )
    return result


def _sse_message(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


ROLE_TITLE_MAP = {
    "principal_investigator": "课题负责人执行记录",
    "literature_assistant": "文献助理执行记录",
    "gap_analyst": "选题分析员执行记录",
    "study_designer": "方案设计师执行记录",
    "meeting_secretary": "组会秘书执行记录",
}


@router.get("/{project_id}/agent-run/stream")
async def stream_project_agent_run(
    project_id: str,
    role: Literal[
        "principal_investigator",
        "literature_assistant",
        "gap_analyst",
        "study_designer",
        "meeting_secretary",
    ],
) -> StreamingResponse:
    project = store.get_project(project_id)

    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")

    async def event_generator():
        yield _sse_message({"type": "status", "message": "OpenClaw 正在接管该角色并准备执行。"})

        try:
            result = await run_openclaw_role(settings, project_id, AgentRunRequest(role=role))
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail, ensure_ascii=False)
            yield _sse_message({"type": "error", "message": detail})
            return

        store.save_generated_document(
            GeneratedDocument(
                id=f"doc_agent_{uuid4().hex[:10]}",
                project_id=project_id,
                doc_type="agent_run",
                title=ROLE_TITLE_MAP[role],
                role=role,
                content=result.content,
                source="openclaw",
                model=result.model,
                session_id=result.session_id,
            )
        )

        yield _sse_message(
            {
                "type": "meta",
                "skill": result.skill,
                "model": result.model,
                "session_id": result.session_id,
                "duration_ms": result.duration_ms,
            }
        )

        for chunk in [segment for segment in result.content.split("\n\n") if segment.strip()]:
            yield _sse_message({"type": "delta", "content": f"{chunk}\n\n"})
            await asyncio.sleep(0.05)

        yield _sse_message({"type": "done"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{project_id}/translate", response_model=TranslateResponse)
async def translate_project_text(project_id: str, payload: TranslateRequest) -> TranslateResponse:
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    source_text = payload.text.strip()
    if not source_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required")
    model, translated = await translate_text(settings, source_text)
    return TranslateResponse(
        project_id=project_id,
        source_text=source_text,
        translated_text=translated.strip(),
        model=model,
    )


@router.post("/{project_id}/follow-up", response_model=FollowUpResponse)
async def follow_up_project(project_id: str, payload: FollowUpRequest) -> FollowUpResponse:
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="question is required")

    state = store.get_state(project_id) or ProjectState(project_id=project_id)
    artifacts = _backfill_artifact_evidence(store.get_artifacts(project_id) or ArtifactBundle())
    knowledge_sources = store.list_knowledge_sources(project_id) or []

    plan_model, follow_up_plan = await plan_follow_up(
        settings,
        project=project,
        state=state,
        artifacts=artifacts,
        knowledge_sources=knowledge_sources,
        question=question,
    )

    delegates_payload = follow_up_plan.get("delegates") or []
    delegates: list[FollowUpDelegate] = []
    for item in delegates_payload[:1]:
        role = item.get("role")
        objective = str(item.get("objective") or "").strip()
        if role in {"literature_assistant", "gap_analyst", "study_designer", "meeting_secretary"} and objective:
            delegates.append(FollowUpDelegate(role=role, objective=objective))

    delegate_results: list[FollowUpDelegateResult] = []
    for delegate in delegates:
        prompt = dedent(
            f"""
            请围绕当前 GUIDECLAW_PROJECT_ID 对应项目执行本轮追问任务。
            用户追问：{question}
            PI 本轮聚焦：{follow_up_plan.get('pi_focus') or state.research_focus or project.title}
            PI 给你的任务：{delegate.objective}

            要求：
            1. 优先使用当前项目已有的知识源、成果卡和证据。
            2. 如果证据不足，要明确指出“目前证据不足”。
            3. 只输出适合科研新人的 Markdown 结果。
            4. 结构建议：结论 / 为什么这么判断 / 还缺什么 / 下一步。
            """
        ).strip()
        try:
            result = await run_openclaw_role(
                settings,
                project_id,
                AgentRunRequest(role=delegate.role, prompt_override=prompt),
            )
            delegate_results.append(
                FollowUpDelegateResult(
                    role=delegate.role,
                    title=ROLE_TITLE_MAP[delegate.role],
                    objective=delegate.objective,
                    status="completed",
                    content=result.content,
                    model=result.model,
                    skill=result.skill,
                    duration_ms=result.duration_ms,
                )
            )
            store.save_generated_document(
                GeneratedDocument(
                    id=f"doc_follow_agent_{uuid4().hex[:10]}",
                    project_id=project_id,
                    doc_type="agent_run",
                    title=f"追问执行 · {ROLE_TITLE_MAP[delegate.role].replace('执行记录', '')}",
                    role=delegate.role,
                    content=result.content,
                    source="openclaw",
                    model=result.model,
                    session_id=result.session_id,
                )
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail, ensure_ascii=False)
            delegate_results.append(
                FollowUpDelegateResult(
                    role=delegate.role,
                    title=ROLE_TITLE_MAP[delegate.role],
                    objective=delegate.objective,
                    status="failed",
                    content=f"执行失败：{detail}",
                )
            )

    result_markdown = "\n".join(
        [
            f"# 追问：{question}",
            "",
            "## PI 本轮判断",
            str(follow_up_plan.get("pi_focus") or state.research_focus or project.title),
            "",
            "## 为什么这样推进",
            str(follow_up_plan.get("why_this_plan") or "本轮追问会优先围绕已有成果和知识源继续推进。"),
            "",
            "## PI 分派给子 Agent 的任务",
            *( [f"- **{ROLE_TITLE_MAP[item.role].replace('执行记录', '')}**：{item.objective}" for item in delegates] or ["- 本轮没有额外子 Agent 任务。"] ),
            "",
            "## 子 Agent 回传",
            *(
                [
                    f"### {item.title.replace('执行记录', '')}\n\n{item.content}"
                    for item in delegate_results
                ]
                or ["当前还没有子 Agent 回传内容。"]
            ),
            "",
            "## 给科研新人的直接建议",
            "- 先看上面各角色给出的结论与证据是否一致。",
            "- 如果结论一致，就把它收成下一步行动；如果不一致，就回到知识库补证据。",
            "- 你可以继续针对一个更具体的问题再追问一次，而不是重新从头做首轮调查。",
        ]
    ).strip()

    store.save_generated_document(
        GeneratedDocument(
            id=f"doc_follow_{uuid4().hex[:10]}",
            project_id=project_id,
            doc_type="follow_up",
            title=f"追问记录 · {question[:24]}",
            content=result_markdown,
            source="system",
            model=plan_model,
        )
    )

    return FollowUpResponse(
        project_id=project_id,
        question=question,
        pi_focus=str(follow_up_plan.get("pi_focus") or state.research_focus or project.title),
        delegates=delegates,
        delegate_results=delegate_results,
        content=result_markdown,
        model=plan_model,
    )
