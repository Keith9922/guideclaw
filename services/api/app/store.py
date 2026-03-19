from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from app.domain.schemas import (
    AgentTask,
    ArtifactBundle,
    GeneratedDocument,
    KnowledgeChunk,
    KnowledgeSource,
    Project,
    ProjectCreate,
    ProjectRecord,
    ProjectState,
    WorkflowStep,
    utc_now,
)


class SQLiteProjectStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL;")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT,
                    stage TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    state_json TEXT NOT NULL DEFAULT '{}',
                    artifacts_json TEXT NOT NULL,
                    workflow_json TEXT NOT NULL
                )
                """
            )
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(projects)").fetchall()
            }
            if "state_json" not in columns:
                connection.execute(
                    "ALTER TABLE projects ADD COLUMN state_json TEXT NOT NULL DEFAULT '{}'"
                )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_sources (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    external_id TEXT,
                    title TEXT NOT NULL,
                    year TEXT,
                    venue TEXT,
                    doi TEXT,
                    url TEXT,
                    abstract TEXT,
                    citation TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    title TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    inputs_json TEXT NOT NULL,
                    expected_output TEXT NOT NULL,
                    output_summary TEXT,
                    depends_on_json TEXT NOT NULL,
                    evidence_source_ids_json TEXT NOT NULL,
                    artifact_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    chunk_type TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    page_from INTEGER,
                    page_to INTEGER,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS generated_documents (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    role TEXT,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    model TEXT,
                    session_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _row_to_record(self, row: sqlite3.Row | None) -> ProjectRecord | None:
        if row is None:
            return None

        project = Project.model_validate(
            {
                "id": row["id"],
                "title": row["title"],
                "summary": row["summary"],
                "stage": row["stage"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
        state_payload = json.loads(row["state_json"]) if row["state_json"] else {}
        state = ProjectState.model_validate({"project_id": project.id, **state_payload})
        artifacts = ArtifactBundle.model_validate_json(row["artifacts_json"])
        workflow_steps = [WorkflowStep.model_validate(item) for item in json.loads(row["workflow_json"])]
        agent_tasks = self._list_agent_tasks(project.id)
        return ProjectRecord(
            project=project,
            state=state,
            artifacts=artifacts,
            workflow_steps=workflow_steps,
            agent_tasks=agent_tasks,
        )

    def list_projects(self) -> list[Project]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        records = [self._row_to_record(row) for row in rows]
        return [record.project for record in records if record is not None]

    def create_project(self, payload: ProjectCreate) -> Project:
        now = utc_now()
        project = Project(
            id=f"proj_{uuid4().hex[:12]}",
            **payload.model_dump(),
            created_at=now,
            updated_at=now,
        )
        artifacts = ArtifactBundle()
        workflow_steps: list[WorkflowStep] = []
        state = ProjectState(project_id=project.id)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO projects (
                    id, title, summary, stage, created_at, updated_at, state_json, artifacts_json, workflow_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.id,
                    project.title,
                    project.summary,
                    project.stage,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                    state.model_dump_json(),
                    artifacts.model_dump_json(),
                    json.dumps([step.model_dump(mode="json") for step in workflow_steps], ensure_ascii=False),
                ),
            )
            connection.commit()
        return project

    def get_project(self, project_id: str) -> Project | None:
        record = self._get_record(project_id)
        return record.project if record else None

    def get_state(self, project_id: str) -> ProjectState | None:
        record = self._get_record(project_id)
        return record.state if record else None

    def delete_project(self, project_id: str) -> bool:
        with self._connect() as connection:
            connection.execute("DELETE FROM knowledge_chunks WHERE project_id = ?", (project_id,))
            connection.execute("DELETE FROM knowledge_sources WHERE project_id = ?", (project_id,))
            connection.execute("DELETE FROM agent_tasks WHERE project_id = ?", (project_id,))
            connection.execute("DELETE FROM generated_documents WHERE project_id = ?", (project_id,))
            cursor = connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            connection.commit()
        return cursor.rowcount > 0

    def get_artifacts(self, project_id: str) -> ArtifactBundle | None:
        record = self._get_record(project_id)
        return record.artifacts if record else None

    def get_workflow_steps(self, project_id: str) -> list[WorkflowStep] | None:
        record = self._get_record(project_id)
        return record.workflow_steps if record else None

    def list_agent_tasks(self, project_id: str) -> list[AgentTask] | None:
        if self.get_project(project_id) is None:
            return None
        return self._list_agent_tasks(project_id)

    def list_knowledge_sources(self, project_id: str) -> list[KnowledgeSource] | None:
        if self.get_project(project_id) is None:
            return None
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM knowledge_sources
                WHERE project_id = ?
                ORDER BY updated_at DESC, created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [self._row_to_knowledge_source(row) for row in rows]

    def list_knowledge_chunks(self, project_id: str) -> list[KnowledgeChunk] | None:
        if self.get_project(project_id) is None:
            return None
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM knowledge_chunks
                WHERE project_id = ?
                ORDER BY source_id ASC, ordinal ASC
                """,
                (project_id,),
            ).fetchall()
        return [self._row_to_knowledge_chunk(row) for row in rows]

    def list_generated_documents(self, project_id: str) -> list[GeneratedDocument] | None:
        if self.get_project(project_id) is None:
            return None
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM generated_documents
                WHERE project_id = ?
                ORDER BY updated_at DESC, created_at DESC
                """,
                (project_id,),
            ).fetchall()
        return [self._row_to_generated_document(row) for row in rows]

    def add_knowledge_source(self, source: KnowledgeSource) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_sources (
                    id, project_id, source_type, external_id, title, year, venue, doi, url,
                    abstract, citation, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.id,
                    source.project_id,
                    source.source_type,
                    source.external_id,
                    source.title,
                    source.year,
                    source.venue,
                    source.doi,
                    source.url,
                    source.abstract,
                    source.citation,
                    source.created_at.isoformat(),
                    source.updated_at.isoformat(),
                ),
            )
            connection.commit()

    def replace_knowledge_sources(self, project_id: str, sources: list[KnowledgeSource]) -> None:
        with self._connect() as connection:
            removable_types = ("openalex", "bohrium_paper_search", "skill_ingest")
            source_rows = connection.execute(
                """
                SELECT id
                FROM knowledge_sources
                WHERE project_id = ?
                AND source_type IN (?, ?, ?)
                """,
                (project_id, *removable_types),
            ).fetchall()
            removable_source_ids = [row["id"] for row in source_rows]
            if removable_source_ids:
                connection.executemany(
                    "DELETE FROM knowledge_chunks WHERE source_id = ?",
                    [(source_id,) for source_id in removable_source_ids],
                )
            connection.execute(
                """
                DELETE FROM knowledge_sources
                WHERE project_id = ?
                AND source_type IN (?, ?, ?)
                """,
                (project_id, *removable_types),
            )
            for source in sources:
                connection.execute(
                    """
                    INSERT INTO knowledge_sources (
                        id, project_id, source_type, external_id, title, year, venue, doi, url,
                        abstract, citation, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source.id,
                        source.project_id,
                        source.source_type,
                        source.external_id,
                        source.title,
                        source.year,
                        source.venue,
                        source.doi,
                        source.url,
                        source.abstract,
                        source.citation,
                        source.created_at.isoformat(),
                        source.updated_at.isoformat(),
                    ),
                )
            connection.commit()

    def replace_source_chunks(self, source_id: str, chunks: list[KnowledgeChunk]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM knowledge_chunks WHERE source_id = ?", (source_id,))
            for chunk in chunks:
                connection.execute(
                    """
                    INSERT INTO knowledge_chunks (
                        id, project_id, source_id, chunk_type, ordinal, content, page_from, page_to, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.id,
                        chunk.project_id,
                        chunk.source_id,
                        chunk.chunk_type,
                        chunk.ordinal,
                        chunk.content,
                        chunk.page_from,
                        chunk.page_to,
                        chunk.created_at.isoformat(),
                    ),
                )
            connection.commit()

    def save_generated_document(self, document: GeneratedDocument) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO generated_documents (
                    id, project_id, doc_type, title, role, content, source, model, session_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    role = excluded.role,
                    content = excluded.content,
                    source = excluded.source,
                    model = excluded.model,
                    session_id = excluded.session_id,
                    updated_at = excluded.updated_at
                """,
                (
                    document.id,
                    document.project_id,
                    document.doc_type,
                    document.title,
                    document.role,
                    document.content,
                    document.source,
                    document.model,
                    document.session_id,
                    document.created_at.isoformat(),
                    document.updated_at.isoformat(),
                ),
            )
            connection.commit()

    def update_research_outputs(
        self,
        project_id: str,
        *,
        stage: str,
        state: ProjectState,
        artifacts: ArtifactBundle,
        workflow_steps: list[WorkflowStep],
        agent_tasks: list[AgentTask],
    ) -> Project | None:
        existing = self._get_record(project_id)
        if existing is None:
            return None

        updated_project = existing.project.model_copy(update={"stage": stage, "updated_at": utc_now()})

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE projects
                SET stage = ?, updated_at = ?, state_json = ?, artifacts_json = ?, workflow_json = ?
                WHERE id = ?
                """,
                (
                    updated_project.stage,
                    updated_project.updated_at.isoformat(),
                    state.model_dump_json(),
                    artifacts.model_dump_json(),
                    json.dumps([step.model_dump(mode="json") for step in workflow_steps], ensure_ascii=False),
                    project_id,
                ),
            )
            connection.execute("DELETE FROM agent_tasks WHERE project_id = ?", (project_id,))
            for task in agent_tasks:
                connection.execute(
                    """
                    INSERT INTO agent_tasks (
                        id, project_id, role, title, objective, status, inputs_json,
                        expected_output, output_summary, depends_on_json,
                        evidence_source_ids_json, artifact_ids_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.id,
                        task.project_id,
                        task.role,
                        task.title,
                        task.objective,
                        task.status,
                        json.dumps(task.inputs, ensure_ascii=False),
                        task.expected_output,
                        task.output_summary,
                        json.dumps(task.depends_on, ensure_ascii=False),
                        json.dumps(task.evidence_source_ids, ensure_ascii=False),
                        json.dumps(task.artifact_ids, ensure_ascii=False),
                        task.created_at.isoformat(),
                        task.updated_at.isoformat(),
                    ),
                )
            connection.commit()

        return updated_project

    def _get_record(self, project_id: str) -> ProjectRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return self._row_to_record(row)

    def _row_to_knowledge_source(self, row: sqlite3.Row) -> KnowledgeSource:
        return KnowledgeSource.model_validate(
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "source_type": row["source_type"],
                "external_id": row["external_id"],
                "title": row["title"],
                "year": row["year"],
                "venue": row["venue"],
                "doi": row["doi"],
                "url": row["url"],
                "abstract": row["abstract"],
                "citation": row["citation"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    def _row_to_knowledge_chunk(self, row: sqlite3.Row) -> KnowledgeChunk:
        return KnowledgeChunk.model_validate(
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "source_id": row["source_id"],
                "chunk_type": row["chunk_type"],
                "ordinal": row["ordinal"],
                "content": row["content"],
                "page_from": row["page_from"],
                "page_to": row["page_to"],
                "created_at": row["created_at"],
            }
        )

    def _row_to_generated_document(self, row: sqlite3.Row) -> GeneratedDocument:
        return GeneratedDocument.model_validate(
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "doc_type": row["doc_type"],
                "title": row["title"],
                "role": row["role"],
                "content": row["content"],
                "source": row["source"],
                "model": row["model"],
                "session_id": row["session_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    def _list_agent_tasks(self, project_id: str) -> list[AgentTask]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM agent_tasks
                WHERE project_id = ?
                ORDER BY created_at ASC, updated_at ASC
                """,
                (project_id,),
            ).fetchall()
        return [self._row_to_agent_task(row) for row in rows]

    def _row_to_agent_task(self, row: sqlite3.Row) -> AgentTask:
        return AgentTask.model_validate(
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "role": row["role"],
                "title": row["title"],
                "objective": row["objective"],
                "status": row["status"],
                "inputs": json.loads(row["inputs_json"]),
                "expected_output": row["expected_output"],
                "output_summary": row["output_summary"],
                "depends_on": json.loads(row["depends_on_json"]),
                "evidence_source_ids": json.loads(row["evidence_source_ids_json"]),
                "artifact_ids": json.loads(row["artifact_ids_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )


InMemoryProjectStore = SQLiteProjectStore
