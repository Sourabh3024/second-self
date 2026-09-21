import json
from pathlib import Path

from secondself.embeddings import cosine_similarity, embed_text
from secondself.link import Linker


def test_embed_text_returns_vector() -> None:
    vector = embed_text("knowledge graph for personal notes")
    assert vector.shape[0] > 0


def test_related_texts_have_high_similarity() -> None:
    left = embed_text("personal knowledge graph for notes and ideas")
    right = embed_text("a graph that stores personal notes and ideas")
    score = cosine_similarity(left, right)
    assert score > 0.5


def test_linker_adds_related_wiki_links(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "wiki"
    for folder in ["Projects", "Areas"]:
        (wiki_dir / folder).mkdir(parents=True)

    note_a = wiki_dir / "Projects" / "cap_a.md"
    note_b = wiki_dir / "Areas" / "cap_b.md"
    note_a.write_text(
        "---\nid: cap_a\ntitle: Building my knowledge graph\ncategory: Projects\ntags: [graph, notes]\nsummary: A knowledge graph for my notes.\nrelated_notes: []\n---\n\nI am building a knowledge graph to organize my notes and ideas.\n",
        encoding="utf-8",
    )
    note_b.write_text(
        "---\nid: cap_b\ntitle: Notes and ideas system\ncategory: Areas\ntags: [ideas, knowledge]\nsummary: A system for personal notes and knowledge.\nrelated_notes: []\n---\n\nThis notes system helps me keep a knowledge graph for my notes and ideas.\n",
        encoding="utf-8",
    )

    linker = Linker(wiki_dir=wiki_dir, data_dir=tmp_path / "data")
    results = linker.link_all()

    assert results
    linked = note_a.read_text(encoding="utf-8")
    assert "[[cap_b]]" in linked or "cap_b" in linked
    assert note_b.read_text(encoding="utf-8")
    assert (tmp_path / "data" / "embeddings").exists()
    index_path = tmp_path / "data" / "embeddings" / "index.json"
    assert index_path.exists()
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert "records" in payload
