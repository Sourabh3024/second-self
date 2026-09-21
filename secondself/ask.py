"""Retrieve relevant wiki notes and synthesize answers from them."""

from __future__ import annotations

import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from secondself.config import settings
from secondself.embeddings import cosine_similarity, embed_text, load_embeddings
from secondself.llm import synthesize_answer

NO_NOTES_ANSWER = "I don't have notes about that."
MAX_CONTEXT_CHARS = 24_000
MIN_RELEVANCE = 0.2


@dataclass(frozen=True)
class AskSource:
    id: str
    summary: str
    relevance_score: float
    para: str


@dataclass(frozen=True)
class AskResult:
    answer: str
    sources: list[AskSource]

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": [asdict(source) for source in self.sources],
        }


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


def _note_text(metadata: dict[str, Any], body: str) -> str:
    return " ".join(
        str(metadata.get(field, "")) for field in ("title", "summary", "tags")
    ) + f" {body}"


def _load_legacy_embeddings(data_dir: Path) -> dict[str, Any]:
    legacy_path = data_dir / "embeddings.pkl"
    if not legacy_path.exists():
        return {}
    try:
        with legacy_path.open("rb") as handle:
            payload = pickle.load(handle)
    except (OSError, EOFError, pickle.PickleError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_notes(wiki_dir: Path) -> dict[str, dict[str, Any]]:
    notes: dict[str, dict[str, Any]] = {}
    for path in sorted(wiki_dir.glob("**/*.md")):
        metadata, body = _read_note(path)
        note_id = str(metadata.get("id") or path.stem).strip()
        if not note_id or note_id in notes:
            continue
        notes[note_id] = {
            "id": note_id,
            "path": path,
            "metadata": metadata,
            "body": body,
            "text": _note_text(metadata, body),
        }
    return notes


def _load_vectors(data_dir: Path) -> dict[str, Any]:
    index_path = data_dir / "embeddings" / "index.json"
    vectors = load_embeddings(index_path)
    if vectors:
        return vectors
    return _load_legacy_embeddings(data_dir)


def _context_for(notes: list[dict[str, Any]]) -> str:
    sections: list[str] = []
    remaining = MAX_CONTEXT_CHARS
    for note in notes:
        metadata = note["metadata"]
        section = (
            f"NOTE [{note['id']}]\n"
            f"Title: {metadata.get('title', '')}\n"
            f"Summary: {metadata.get('summary', '')}\n"
            f"PARA: {metadata.get('category') or metadata.get('para') or ''}\n"
            f"Content: {note['body']}\n"
        )
        if len(section) > remaining:
            section = section[:remaining]
        if not section:
            break
        sections.append(section)
        remaining -= len(section)
        if remaining <= 0:
            break
    return "\n".join(sections)


def ask(
    question: str,
    top_k: int = 5,
    *,
    wiki_dir: str | Path | None = None,
    data_dir: str | Path | None = None,
    min_relevance: float = MIN_RELEVANCE,
) -> AskResult:
    """Answer a question from the most relevant notes in the wiki."""
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Question must not be empty")
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    if not 0 <= min_relevance <= 1:
        raise ValueError("min_relevance must be between 0 and 1")

    notes = _load_notes(Path(wiki_dir or settings.wiki_dir))
    if not notes:
        return AskResult(answer=NO_NOTES_ANSWER, sources=[])

    root_data_dir = Path(data_dir or settings.data_dir)
    vectors = _load_vectors(root_data_dir)
    question_vector = embed_text(cleaned_question)
    scored: list[tuple[float, dict[str, Any]]] = []
    for note_id, note in notes.items():
        vector = vectors.get(note_id)
        if vector is None:
            vector = embed_text(note["text"])
        score = cosine_similarity(question_vector, vector)
        scored.append((score, note))

    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    selected = [(score, note) for score, note in scored if score >= min_relevance][:top_k]
    if not selected:
        return AskResult(answer=NO_NOTES_ANSWER, sources=[])

    selected_notes = [note for _, note in selected]
    sources = [
        AskSource(
            id=note["id"],
            summary=str(note["metadata"].get("summary") or note["body"][:180]),
            relevance_score=round(float(score), 6),
            para=str(
                note["metadata"].get("category")
                or note["metadata"].get("para")
                or note["path"].parent.name
            ),
        )
        for score, note in selected
    ]
    answer = synthesize_answer(_context_for(selected_notes), cleaned_question)
    return AskResult(answer=answer, sources=sources)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Ask questions of the SecondSelf wiki.")
    parser.add_argument("question", help="Natural-language question")
    parser.add_argument("--top-k", type=int, default=settings.top_k)
    args = parser.parse_args()
    print(json.dumps(ask(args.question, top_k=args.top_k).to_dict(), indent=2))


if __name__ == "__main__":
    main()
