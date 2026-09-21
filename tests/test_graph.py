import json
from pathlib import Path

from secondself.graph import build_graph, write_graph


def _write_note(path: Path, note_id: str, category: str, body: str, links: list[str]) -> None:
    path.write_text(
        "---\n"
        f"id: {note_id}\n"
        f"category: {category}\n"
        "tags: [knowledge, graph]\n"
        f"summary: Summary for {note_id}\n"
        f"related_notes: {links}\n"
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )


def test_build_graph_creates_nodes_and_deduplicates_edges(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki" / "Projects"
    wiki_dir.mkdir(parents=True)
    _write_note(
        wiki_dir / "note_a.md",
        "note_a",
        "Projects",
        "A body with a link to [[note_b]].",
        ["note_b"],
    )
    _write_note(
        wiki_dir / "note_b.md",
        "note_b",
        "Areas",
        "A reciprocal link to [[note_a]].",
        ["note_a"],
    )

    graph = build_graph(tmp_path / "wiki")

    assert graph["metadata"]["node_count"] == 2
    assert graph["metadata"]["edge_count"] == 1
    assert graph["nodes"][0]["content_preview"] == "A body with a link to ."
    assert graph["edges"] == [
        {"source": "note_a", "target": "note_b", "weight": 1.0, "type": "wikilink"}
    ]


def test_write_graph_creates_parent_directory_and_valid_json(tmp_path: Path) -> None:
    output = tmp_path / "data" / "graph.json"

    path = write_graph({"nodes": [], "edges": [], "metadata": {}}, output)

    assert path == output
    assert json.loads(output.read_text(encoding="utf-8"))["nodes"] == []
