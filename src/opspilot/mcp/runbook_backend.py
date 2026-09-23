"""Simple local runbook search backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class RunbookBackend:
    """Search checked-in Markdown runbooks without external credentials."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path("data/runbooks")

    def search(self, query: str) -> list[dict[str, Any]]:
        terms = [term.lower() for term in query.split() if term.strip()]
        matches: list[dict[str, Any]] = []
        for path in sorted(self.directory.glob("*.md")):
            text = path.read_text()
            haystack = text.lower()
            if not terms or all(term in haystack for term in terms):
                matches.append(
                    {"runbook_id": path.stem, "title": text.splitlines()[0], "snippet": text[:600]}
                )
        return matches

    def get(self, runbook_id: str) -> dict[str, str]:
        path = self.directory / f"{runbook_id}.md"
        if not path.exists():
            raise KeyError(f"unknown runbook: {runbook_id}")
        return {"runbook_id": runbook_id, "content": path.read_text()}
