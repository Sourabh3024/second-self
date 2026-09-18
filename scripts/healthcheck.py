"""Verify that the Phase 0 project foundation is usable."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from secondself.config import settings  # noqa: E402


REQUIRED_DIRECTORIES = (
    settings.raw_dir / "captures",
    settings.raw_dir / "attachments",
    settings.wiki_dir / "Projects",
    settings.wiki_dir / "Areas",
    settings.wiki_dir / "Resources",
    settings.wiki_dir / "Archives",
    settings.data_dir / "embeddings",
)


def main() -> int:
    missing = [path for path in REQUIRED_DIRECTORIES if not path.is_dir()]
    if missing:
        print("Missing required directories:")
        for path in missing:
            print(f"- {path}")
        return 1

    print("SecondSelf foundation is ready.")
    print(f"Project root: {settings.project_root}")
    print(f"Embedding model: {settings.embedding_model}")
    print(f"Similarity threshold: {settings.similarity_threshold}")
    print(f"Top K: {settings.top_k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
