from pathlib import Path

from secondself.ask import NO_NOTES_ANSWER, ask


def _write_note(path: Path, note_id: str, summary: str, body: str) -> None:
    path.write_text(
        "---\n"
        f"id: {note_id}\n"
        "title: Test note\n"
        "category: Resources\n"
        "tags: [test]\n"
        f"summary: {summary}\n"
        "related_notes: []\n"
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )


def test_ask_retrieves_notes_and_returns_sources(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki" / "Resources"
    wiki_dir.mkdir(parents=True)
    _write_note(
        wiki_dir / "excel.md",
        "excel",
        "Excel course resource",
        "I saved an Excel mastery course for improving spreadsheet skills.",
    )

    result = ask(
        "Which Excel course did I save?",
        top_k=1,
        wiki_dir=tmp_path / "wiki",
        data_dir=tmp_path / "data",
    )

    assert "Excel" in result.answer
    assert [source.id for source in result.sources] == ["excel"]
    assert result.sources[0].para == "Resources"
    assert result.sources[0].relevance_score >= 0.2


def test_ask_returns_guardrail_for_empty_or_irrelevant_wiki(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki" / "Resources"
    wiki_dir.mkdir(parents=True)
    _write_note(wiki_dir / "weather.md", "weather", "Weather note", "Rain is expected tomorrow.")

    result = ask(
        "What is my investment portfolio?",
        wiki_dir=tmp_path / "wiki",
        data_dir=tmp_path / "data",
    )

    assert result.answer == NO_NOTES_ANSWER
    assert result.sources == []


def test_ask_rejects_invalid_questions_and_options(tmp_path: Path) -> None:
    for question in ("", "   "):
        try:
            ask(question, wiki_dir=tmp_path / "wiki", data_dir=tmp_path / "data")
        except ValueError:
            pass
        else:
            raise AssertionError("empty question should fail")

    try:
        ask("anything", top_k=0, wiki_dir=tmp_path / "wiki", data_dir=tmp_path / "data")
    except ValueError:
        pass
    else:
        raise AssertionError("top_k=0 should fail")