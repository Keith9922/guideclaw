from __future__ import annotations

import re
from collections import Counter

from app.domain.schemas import KnowledgeChunk, KnowledgeHit, KnowledgeSource


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^\w\u4e00-\u9fff]+", text.lower()) if token]


def _score_text(query_counter: Counter[str], normalized_query: str, text: str, title: str) -> float:
    source_terms = Counter(_tokenize(text))
    overlap = sum(min(source_terms[term], count) for term, count in query_counter.items())
    phrase_bonus = 3 if normalized_query in text else 0
    title_bonus = 2 if normalized_query in title.lower() else 0
    return float(overlap + phrase_bonus + title_bonus)


def search_project_knowledge(
    sources: list[KnowledgeSource],
    chunks: list[KnowledgeChunk],
    query: str,
    *,
    limit: int = 8,
) -> list[KnowledgeHit]:
    normalized_query = query.strip().lower()
    if not normalized_query:
        normalized_query = ""
    query_terms = _tokenize(normalized_query)
    if not query_terms and normalized_query:
        query_terms = [normalized_query]
    query_counter = Counter(query_terms)

    source_map = {source.id: source for source in sources}
    hits: list[KnowledgeHit] = []

    if chunks:
      candidate_chunks = chunks
    else:
      candidate_chunks = []

    if candidate_chunks and query_counter:
        for chunk in candidate_chunks:
            source = source_map.get(chunk.source_id)
            if source is None:
                continue
            haystack = f"{source.title}\n{chunk.content}".lower()
            score = _score_text(query_counter, normalized_query, haystack, source.title)
            if score <= 0:
                continue
            hits.append(
                KnowledgeHit(
                    source_id=source.id,
                    chunk_id=chunk.id,
                    source_type=source.source_type,
                    title=source.title,
                    excerpt=chunk.content[:320],
                    score=score,
                    page_from=chunk.page_from,
                    page_to=chunk.page_to,
                    citation=source.citation,
                    doi=source.doi,
                    url=source.url,
                )
            )

    if not hits:
        for source in sources:
            excerpt = source.abstract or source.citation or source.title
            haystack = " ".join(
                part for part in [source.title, source.venue or "", excerpt, source.doi or ""] if part
            ).lower()
            score = _score_text(query_counter, normalized_query, haystack, source.title) if query_counter else 1.0
            if score <= 0:
                continue
            hits.append(
                KnowledgeHit(
                    source_id=source.id,
                    chunk_id=None,
                    source_type=source.source_type,
                    title=source.title,
                    excerpt=excerpt[:320],
                    score=score,
                    citation=source.citation,
                    doi=source.doi,
                    url=source.url,
                )
            )

    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[:limit]
