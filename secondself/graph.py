"""Build a JSON knowledge graph from classified wiki notes."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from secondself.config import settings

WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def _read_note(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            metadata = yaml.safe_load(parts[1]) or {}
            if not isinstance(metadata, dict):
                metadata = {}
            return metadata, parts[2].strip()
    return {}, text.strip()


def _note_id(path: Path, metadata: dict[str, Any]) -> str:
    value = metadata.get("id")
    return str(value).strip() if value else path.stem


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _content_preview(body: str, limit: int = 200) -> str:
    without_links = WIKILINK_PATTERN.sub("", body)
    compact = " ".join(without_links.split())
    return compact[:limit]


def _link_ids(metadata: dict[str, Any], body: str) -> set[str]:
    related = set(_as_string_list(metadata.get("related_notes")))
    related.update(_as_string_list(metadata.get("links")))
    related.update(match.group(1).strip() for match in WIKILINK_PATTERN.finditer(body))
    return {note_id for note_id in related if note_id}


def build_graph(wiki_dir: str | Path | None = None) -> dict[str, Any]:
    """Build nodes and deduplicated undirected edges from wiki Markdown files."""
    root = Path(wiki_dir or settings.wiki_dir)
    notes: dict[str, dict[str, Any]] = {}
    relationships: set[tuple[str, str]] = set()

    for path in sorted(root.glob("**/*.md")):
        metadata, body = _read_note(path)
        note_id = _note_id(path, metadata)
        if note_id in notes:
            raise ValueError(f"Duplicate wiki note id {note_id!r}: {path}")

        category = str(metadata.get("category") or path.parent.name)
        tags = _as_string_list(metadata.get("tags"))
        summary = str(metadata.get("summary") or metadata.get("title") or "")
        notes[note_id] = {
            "id": note_id,
            "label": summary,
            "para": category,
            "tags": tags,
            "summary": summary,
            "content_preview": _content_preview(body),
            "group": category,
        }

        for target in _link_ids(metadata, body):
            if target == note_id:
                continue
            source, destination = sorted((note_id, target))
            relationships.add((source, destination))

    edges = [
        {
            "source": source,
            "target": target,
            "weight": 1.0,
            "type": "wikilink",
        }
        for source, target in sorted(relationships)
        if source in notes and target in notes
    ]

    return {
        "nodes": [notes[note_id] for note_id in sorted(notes)],
        "edges": edges,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "node_count": len(notes),
            "edge_count": len(edges),
        },
    }


def write_graph(
    graph: dict[str, Any], output_path: str | Path | None = None
) -> Path:
    """Write a graph payload as formatted JSON and return its path."""
    destination = Path(output_path or settings.data_dir / "graph.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    return destination


def build_and_write_graph(
    wiki_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    graph = build_graph(wiki_dir)
    return graph, write_graph(graph, output_path)
