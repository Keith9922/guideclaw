from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from app.domain.schemas import KnowledgeChunk, KnowledgeSource


def _chunk_text(text: str, *, size: int = 900) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[。！？.!?])\s+", normalized):
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 <= size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def build_source_chunks(source: KnowledgeSource) -> list[KnowledgeChunk]:
    seed_text = source.abstract or source.citation or source.title
    chunks = _chunk_text(seed_text, size=600)
    if not chunks:
        return []
    return [
        KnowledgeChunk(
            id=f"chunk_{uuid4().hex[:12]}",
            project_id=source.project_id,
            source_id=source.id,
            chunk_type="abstract",
            ordinal=index,
            content=chunk,
        )
        for index, chunk in enumerate(chunks, start=1)
    ]


def ingest_pdf(
    project_id: str,
    source_id: str,
    file_path: Path,
) -> tuple[str, list[KnowledgeChunk]]:
    reader = PdfReader(str(file_path))
    all_chunks: list[KnowledgeChunk] = []
    preview_parts: list[str] = []

    for page_index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        if len(preview_parts) < 2:
            preview_parts.append(text[:700])
        page_chunks = _chunk_text(text, size=1000)
        for chunk_index, chunk in enumerate(page_chunks, start=1):
            all_chunks.append(
                KnowledgeChunk(
                    id=f"chunk_{uuid4().hex[:12]}",
                    project_id=project_id,
                    source_id=source_id,
                    chunk_type="pdf_text",
                    ordinal=len(all_chunks) + 1,
                    content=chunk,
                    page_from=page_index,
                    page_to=page_index,
                )
            )

    preview = "\n\n".join(preview_parts).strip()
    return preview[:1500], all_chunks
