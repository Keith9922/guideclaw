from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceSnippet(BaseModel):
    source: str
    source_id: str | None = None
    chunk_id: str | None = None
    source_type: Literal["openalex", "bohrium_paper_search", "pdf_upload", "manual", "skill_ingest"] | None = None
    page: int | None = None
    page_to: int | None = None
    snippet: str
    citation: str | None = None
    doi: str | None = None
    url: str | None = None


class ProjectBase(BaseModel):
    title: str
    summary: str | None = None
    stage: Literal["literature_review", "gap_analysis", "proposal", "meeting_notes"] = (
        "literature_review"
    )


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase):
    id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProjectState(BaseModel):
    project_id: str
    research_focus: str = ""
    why_now: str = ""
    key_questions: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    recommended_gap_title: str | None = None
    current_hypothesis: str | None = None
    next_step: str | None = None
    literature_provider: str | None = None
    provider_note: str | None = None
    last_investigated_at: datetime | None = None


class LiteratureCard(BaseModel):
    id: str
    project_id: str
    title: str
    research_question: str
    method: str
    data_source: str
    key_result: str
    limitations: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSnippet] = Field(default_factory=list)


class GapCard(BaseModel):
    id: str
    project_id: str
    title: str
    gap_type: str
    why_it_matters: str
    novelty_score: int = Field(ge=0, le=10)
    importance_score: int = Field(ge=0, le=10)
    feasibility_score: int = Field(ge=0, le=10)
    evidence: list[EvidenceSnippet] = Field(default_factory=list)


class PlanCard(BaseModel):
    id: str
    project_id: str
    research_question: str
    boundary: str
    data_source: str
    metrics: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    validation: str
    evidence: list[EvidenceSnippet] = Field(default_factory=list)


class MeetingNote(BaseModel):
    id: str
    project_id: str
    decisions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    todos: list[str] = Field(default_factory=list)
    next_step: str
    evidence: list[EvidenceSnippet] = Field(default_factory=list)


class ArtifactBundle(BaseModel):
    literature_cards: list[LiteratureCard] = Field(default_factory=list)
    gap_cards: list[GapCard] = Field(default_factory=list)
    plan_cards: list[PlanCard] = Field(default_factory=list)
    meeting_notes: list[MeetingNote] = Field(default_factory=list)


class WorkflowStep(BaseModel):
    role: Literal[
        "principal_investigator",
        "literature_assistant",
        "gap_analyst",
        "study_designer",
        "meeting_secretary",
    ]
    title: str
    summary: str


class AgentTask(BaseModel):
    id: str
    project_id: str
    role: Literal[
        "principal_investigator",
        "literature_assistant",
        "gap_analyst",
        "study_designer",
        "meeting_secretary",
    ]
    title: str
    objective: str
    status: Literal["pending", "running", "completed", "blocked"] = "pending"
    inputs: list[str] = Field(default_factory=list)
    expected_output: str = ""
    output_summary: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    evidence_source_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class KnowledgeSource(BaseModel):
    id: str
    project_id: str
    source_type: Literal["openalex", "bohrium_paper_search", "pdf_upload", "manual", "skill_ingest"] = (
        "openalex"
    )
    external_id: str | None = None
    title: str
    year: str | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
    citation: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class KnowledgeChunk(BaseModel):
    id: str
    project_id: str
    source_id: str
    chunk_type: Literal["abstract", "pdf_text", "note"] = "abstract"
    ordinal: int
    content: str
    page_from: int | None = None
    page_to: int | None = None
    created_at: datetime = Field(default_factory=utc_now)


class KnowledgeHit(BaseModel):
    source_id: str
    chunk_id: str | None = None
    source_type: Literal["openalex", "bohrium_paper_search", "pdf_upload", "manual", "skill_ingest"]
    title: str
    excerpt: str
    score: float
    page_from: int | None = None
    page_to: int | None = None
    citation: str | None = None
    doi: str | None = None
    url: str | None = None


class GeneratedDocument(BaseModel):
    id: str
    project_id: str
    doc_type: Literal["project_summary", "agent_run", "follow_up", "result_summary"]
    title: str
    role: Literal[
        "principal_investigator",
        "literature_assistant",
        "gap_analyst",
        "study_designer",
        "meeting_secretary",
    ] | None = None
    content: str
    source: Literal["openrouter", "openclaw", "system"] = "openrouter"
    model: str | None = None
    session_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProjectRecord(BaseModel):
    project: Project
    state: ProjectState
    artifacts: ArtifactBundle = Field(default_factory=ArtifactBundle)
    workflow_steps: list[WorkflowStep] = Field(default_factory=list)
    agent_tasks: list[AgentTask] = Field(default_factory=list)


class LlmSummaryResponse(BaseModel):
    project_id: str
    model: str
    source: Literal["openrouter"] = "openrouter"
    content: str


class AgentRunRequest(BaseModel):
    role: Literal[
        "principal_investigator",
        "literature_assistant",
        "gap_analyst",
        "study_designer",
        "meeting_secretary",
    ]
    prompt_override: str | None = None


class AgentRunResponse(BaseModel):
    project_id: str
    role: Literal[
        "principal_investigator",
        "literature_assistant",
        "gap_analyst",
        "study_designer",
        "meeting_secretary",
    ]
    skill: str
    model: str | None = None
    session_id: str | None = None
    duration_ms: int | None = None
    content: str


class InvestigationResponse(BaseModel):
    project: Project
    research_state: ProjectState
    artifacts: ArtifactBundle
    workflow_steps: list[WorkflowStep] = Field(default_factory=list)
    agent_tasks: list[AgentTask] = Field(default_factory=list)


class TranslateRequest(BaseModel):
    text: str


class TranslateResponse(BaseModel):
    project_id: str
    source_text: str
    translated_text: str
    model: str | None = None


class FollowUpDelegate(BaseModel):
    role: Literal[
        "literature_assistant",
        "gap_analyst",
        "study_designer",
        "meeting_secretary",
    ]
    objective: str


class FollowUpRequest(BaseModel):
    question: str


class FollowUpDelegateResult(BaseModel):
    role: Literal[
        "literature_assistant",
        "gap_analyst",
        "study_designer",
        "meeting_secretary",
    ]
    title: str
    objective: str
    status: Literal["completed", "failed"]
    content: str
    model: str | None = None
    skill: str | None = None
    duration_ms: int | None = None


class FollowUpResponse(BaseModel):
    project_id: str
    question: str
    pi_focus: str
    delegates: list[FollowUpDelegate] = Field(default_factory=list)
    delegate_results: list[FollowUpDelegateResult] = Field(default_factory=list)
    content: str
    model: str | None = None


class ResultSummaryReference(BaseModel):
    title: str
    reason: str
    citation: str | None = None
    doi: str | None = None
    url: str | None = None
    source_type: Literal["openalex", "bohrium_paper_search", "pdf_upload", "manual", "skill_ingest"] | None = None


class ResultSummarySection(BaseModel):
    title: str
    content: str
    bullets: list[str] = Field(default_factory=list)


class ResultSummaryAction(BaseModel):
    title: str
    description: str


class ResultSummaryResponse(BaseModel):
    project_id: str
    project_title: str
    stage_label: str
    intro: str
    sections: list[ResultSummarySection] = Field(default_factory=list)
    recommended_reading: list[ResultSummaryReference] = Field(default_factory=list)
    next_actions: list[ResultSummaryAction] = Field(default_factory=list)
    knowledge_highlights: list[ResultSummaryReference] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    pdf_url: str


class ProjectWorkspace(BaseModel):
    project: Project
    research_state: ProjectState
    artifacts: ArtifactBundle
    workflow_steps: list[WorkflowStep] = Field(default_factory=list)
    agent_tasks: list[AgentTask] = Field(default_factory=list)
    knowledge_sources: list[KnowledgeSource] = Field(default_factory=list)
    generated_documents: list[GeneratedDocument] = Field(default_factory=list)


class PdfUploadResponse(BaseModel):
    source: KnowledgeSource
    chunk_count: int
