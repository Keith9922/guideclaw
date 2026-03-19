from __future__ import annotations

import re

import httpx

from app.settings import Settings


def _build_search_words(query: str) -> list[str]:
    normalized = query.replace(" OR ", "\n").replace("，", "\n").replace(",", "\n")
    candidates = [item.strip() for item in normalized.splitlines() if item.strip()]
    if not candidates:
        candidates = [query.strip()]

    words: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        compact = re.sub(r"\s+", " ", candidate).strip()
        if len(compact) < 2 or compact.lower() in seen:
            continue
        seen.add(compact.lower())
        words.append(compact)
        if len(words) >= 6:
            break
    return words or [query.strip()]


async def search_bohrium_papers(
    settings: Settings,
    query: str,
    *,
    per_page: int = 4,
) -> list[dict[str, str]]:
    if not settings.bohrium_ready or not settings.bohrium_access_key:
        return []

    payload = {
        "words": _build_search_words(query),
        "question": query,
        "type": 5,
        "pageSize": per_page,
    }
    headers = {
        "accessKey": settings.bohrium_access_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{settings.bohrium_openapi_base_url.rstrip('/')}/paper/rag/pass/keyword",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    body = response.json()
    items = body.get("data") or []
    works: list[dict[str, str]] = []
    for item in items:
        title = str(item.get("enName") or item.get("zhName") or "未命名论文").strip()
        venue = str(item.get("publicationEnName") or item.get("publicationZhName") or "Bohrium").strip()
        doi = str(item.get("doi") or "").strip()
        url = str(item.get("paperLink") or item.get("url") or (f"https://doi.org/{doi}" if doi else "")).strip()
        year = str(item.get("coverDateStart") or item.get("publicationYear") or "").strip()
        if year and len(year) >= 4:
            year = year[:4]
        abstract = str(item.get("enAbstract") or item.get("zhAbstract") or "").strip()
        pieces = item.get("pieces") or []
        snippet = abstract
        if not snippet and isinstance(pieces, list):
            for piece in pieces:
                if isinstance(piece, str) and piece.strip():
                    snippet = piece.strip()
                    break
                if isinstance(piece, dict):
                    for key in ("text", "content", "snippet"):
                        value = piece.get(key)
                        if isinstance(value, str) and value.strip():
                            snippet = value.strip()
                            break
                    if snippet:
                        break

        works.append(
            {
                "provider": "bohrium",
                "source_type": "bohrium_paper_search",
                "external_id": str(item.get("paperId") or doi or url or title).strip(),
                "title": title,
                "year": year,
                "abstract": snippet,
                "source": venue,
                "doi": doi,
                "url": url,
            }
        )
    return works
