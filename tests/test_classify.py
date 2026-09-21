import json
from pathlib import Path

import pytest

from secondself.classify import Classifier, classify_content


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Build a personal AI knowledge graph for my research notes.", "Projects"),
        ("I need a better habit for weekly review and writing consistency.", "Areas"),
        ("A guide to vector search and sentence-transformers embeddings.", "Resources"),
        ("Old meeting notes from last quarter that are no longer active.", "Archives"),
    ],
)
def test_classify_content_returns_valid_para_category(text: str, expected: str) -> None:
    result = classify_content(text)
    assert result["category"] in {"Projects", "Areas", "Resources", "Archives"}
    assert result["category"] == expected
    assert isinstance(result["tags"], list) and result["tags"]
    assert result["summary"]
    assert result["title"]


def test_classifier_writes_markdown_note_for_capture(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True)
    capture_dir = raw_dir / "captures"
    capture_dir.mkdir()
    capture_id = "cap_20260921_test123"
    capture_path = capture_dir / f"{capture_id}.json"
    capture_path.write_text(
        json.dumps(
            {
                "id": capture_id,
                "type": "note",
                "title": "Career planning",
                "content": "I am planning a switch into ML engineering and need a pipeline for portfolio work.",
                "captured_at": "2026-09-21T00:00:00Z",
                "status": "unprocessed",
            }
        ),
        encoding="utf-8",
    )

    classifier = Classifier(raw_dir=raw_dir, wiki_dir=tmp_path / "wiki", data_dir=tmp_path / "data")
    result = classifier.process_capture(capture_path)

    assert result["category"] in {"Projects", "Areas", "Resources", "Archives"}
    assert result["wiki_path"].endswith(".md")
    wiki_note = Path(result["wiki_path"])
    assert wiki_note.is_file()
    assert "---" in wiki_note.read_text(encoding="utf-8")
    assert result["status"] == "classified"
