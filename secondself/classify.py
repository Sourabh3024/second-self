"""Auto-classify raw captures into PARA-based wiki notes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from secondself.config import settings
from secondself.llm import classify_content


VALID_CATEGORIES = {"Projects", "Areas", "Resources", "Archives"}


class ClassificationError(ValueError):
    """Raised when a raw capture cannot be classified or written safely."""


class Classifier:
    def __init__(
        self,
        raw_dir: str | Path | None = None,
        wiki_dir: str | Path | None = None,
        data_dir: str | Path | None = None,
    ) -> None:
        self.raw_dir = Path(raw_dir or settings.raw_dir)
        self.wiki_dir = Path(wiki_dir or settings.wiki_dir)
        self.data_dir = Path(data_dir or settings.data_dir)
        self.index_path = self.data_dir / "index.json"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            payload = {"raw_processed": {}, "embeddings_version": "all-MiniLM-L6-v2", "last_graph_build": None}
            self.index_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _persist_index(self, payload: dict[str, Any]) -> None:
        self.index_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _capture_text(self, record: dict[str, Any]) -> str:
        if isinstance(record.get("content"), str) and record["content"].strip():
            return record["content"].strip()
        if isinstance(record.get("url"), str) and record["url"].strip():
            return record["url"].strip()
        file_path = record.get("file_path")
        if isinstance(file_path, str) and file_path:
            candidate = self.raw_dir / file_path
            if candidate.exists():
                return candidate.name
        return record.get("title") or "Captured item"

    def _write_wiki_note(self, record: dict[str, Any], classification: dict[str, Any]) -> str:
        category = classification["category"]
        if category not in VALID_CATEGORIES:
            raise ClassificationError(f"Unsupported category: {category}")

        category_dir = self.wiki_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        capture_id = str(record.get("id") or record.get("title") or "capture")
        note_id = capture_id.replace("/", "_")
        file_path = category_dir / f"{note_id}.md"
        content = record.get("content") or record.get("url") or record.get("title") or "No content available."
        frontmatter = {
            "id": note_id,
            "title": classification["title"],
            "category": category,
            "tags": classification["tags"],
            "summary": classification["summary"],
            "created_at": record.get("captured_at") or datetime.now(timezone.utc).isoformat(),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "raw_id": capture_id,
            "related_notes": [],
            "embedding_model": "pending",
        }
        text = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True) + "---\n\n" + str(content) + "\n"
        file_path.write_text(text, encoding="utf-8")
        return str(file_path)

    def process_capture(self, capture_path: str | Path) -> dict[str, Any]:
        capture_file = Path(capture_path)
        payload = json.loads(capture_file.read_text(encoding="utf-8"))
        capture_id = str(payload.get("id") or capture_file.stem)
        classification = classify_content(self._capture_text(payload))
        wiki_path = self._write_wiki_note(payload, classification)

        index = self._index()
        index.setdefault("raw_processed", {})
        index["raw_processed"][capture_id] = {
            "status": "classified",
            "category": classification["category"],
            "wiki_path": wiki_path,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        self._persist_index(index)

        return {
            "id": capture_id,
            "category": classification["category"],
            "tags": classification["tags"],
            "summary": classification["summary"],
            "title": classification["title"],
            "status": "classified",
            "wiki_path": wiki_path,
        }

    def process_all(self) -> list[dict[str, Any]]:
        capture_dir = self.raw_dir / "captures"
        if not capture_dir.exists():
            return []

        results: list[dict[str, Any]] = []
        for capture_file in sorted(capture_dir.glob("*.json")):
            index = self._index()
            capture_id = capture_file.stem
            if capture_id in index.get("raw_processed", {}):
                continue
            results.append(self.process_capture(capture_file))
        return results
