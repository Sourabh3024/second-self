from pathlib import Path

from secondself.config import PROJECT_ROOT, settings


def test_settings_point_to_project_root() -> None:
    assert PROJECT_ROOT.is_dir()
    assert settings.raw_dir == PROJECT_ROOT / "raw"
    assert settings.wiki_dir == PROJECT_ROOT / "wiki"
    assert settings.data_dir == PROJECT_ROOT / "data"


def test_settings_have_valid_defaults() -> None:
    settings.validate()
    assert settings.similarity_threshold == 0.68
    assert settings.top_k == 5
    assert settings.embedding_model
