from __future__ import annotations

from pathlib import Path
from typing import Protocol


class GrobidParserPort(Protocol):
    async def parse_pdf(self, pdf_path: Path) -> dict: ...


class PyAlexCatalogPort(Protocol):
    async def search(self, query: str) -> list[dict]: ...


class PaperQAPort(Protocol):
    async def answer(self, question: str, *, context: list[str]) -> str: ...
