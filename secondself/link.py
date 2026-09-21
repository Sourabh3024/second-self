"""Link related wiki notes using local embeddings and cosine similarity."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from secondself.config import settings
from secondself.embeddings import (
    cosine_similarity,
    embed_text,
    ensure_storage,
    lexical_similarity,
    load_embeddings,
    save_embeddings,
)


class Linker:
    def __init__(self, wiki_dir: str | Path | None = None, data_dir: str | Path | None = None) -> None:
        self.wiki_dir = Path(wiki_dir or settings.wiki_dir)
        self.data_dir = Path(data_dir or settings.data_dir)
        self.embedding_dir = ensure_storage(self.data_dir)
        self.index_path = self.embedding_dir / "index.json"

    def _iter_notes(self) -> list[Path]:
        return sorted(self.wiki_dir.glob("**/*.md"))

    def _read_markdown(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        if text.startswith("---\n"):
            parts = text.split("---\n", 2)
            if len(parts) == 3:
                meta = yaml.safe_load(parts[1]) or {}
                return {"meta": meta, "body": parts[2].strip()}
        return {"meta": {}, "body": text.strip()}

    def _note_text(self, path: Path) -> str:
        payload = self._read_markdown(path)
        meta = payload["meta"]
        body = payload["body"]
        return " ".join([
            str(meta.get("title", "")),
            str(meta.get("summary", "")),
            body,
        ])

    def _write_note(self, path: Path, related: list[str]) -> None:
        payload = self._read_markdown(path)
        meta = dict(payload["meta"])
        meta["related_notes"] = sorted(set(related))
        body = payload["body"]
        links = "\n".join(f"[[{note_id}]]" for note_id in meta["related_notes"])
        if links:
            body = body.rstrip() + "\n\n" + links + "\n"
        frontmatter = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
        path.write_text(f"---\n{frontmatter}---\n\n{body}\n", encoding="utf-8")

    def link_all(self) -> list[dict[str, Any]]:
        notes = self._iter_notes()
        if not notes:
            return []

        vectors: dict[str, Any] = load_embeddings(self.index_path)
        rows: list[dict[str, Any]] = []
        for note in notes:
            note_id = note.stem
            if note_id not in vectors:
                vectors[note_id] = embed_text(self._note_text(note))
            rows.append({"id": note_id, "path": note, "text": self._note_text(note)})

        results: list[dict[str, Any]] = []
        for row in rows:
            related: list[str] = []
            for other in rows:
                if other["id"] == row["id"]:
                    continue
                lexical_score = lexical_similarity(row["text"], other["text"])
                vector_score = cosine_similarity(vectors[row["id"]], vectors[other["id"]])
                score = max(vector_score, lexical_score)
                if score >= settings.similarity_threshold:
                    related.append(other["id"])
            related = sorted(set(related))
            if related:
                self._write_note(row["path"], related)
            results.append({"id": row["id"], "related": related})

        save_embeddings(vectors, self.index_path)
        return results


def link_all(wiki_dir: str | Path | None = None, data_dir: str | Path | None = None) -> list[dict[str, Any]]:
    return Linker(wiki_dir=wiki_dir, data_dir=data_dir).link_all()
