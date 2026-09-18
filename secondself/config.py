"""Central configuration for the SecondSelf project.

The module has no external dependency, so local setup and health checks work
before optional AI packages or API keys are installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # Optional during lightweight health checks.
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_CATEGORIES = ("Projects", "Areas", "Resources", "Archives")

if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")


def _path_from_env(name: str, default: str) -> Path:
    value = os.getenv(name, default).strip()
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _float_from_env(name: str, default: float) -> float:
    value = os.getenv(name, str(default)).strip()
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def _int_from_env(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


@dataclass(frozen=True)
class Settings:
    project_root: Path
    raw_dir: Path
    wiki_dir: Path
    data_dir: Path
    embedding_model: str
    similarity_threshold: float
    top_k: int
    llm_provider: str
    llm_model: str

    def validate(self) -> None:
        if not self.embedding_model:
            raise ValueError("EMBEDDING_MODEL must not be empty")
        if not 0 <= self.similarity_threshold <= 1:
            raise ValueError("SIMILARITY_THRESHOLD must be between 0 and 1")
        if self.top_k < 1:
            raise ValueError("TOP_K must be at least 1")
        if not self.llm_provider:
            raise ValueError("LLM_PROVIDER must not be empty")
        if not self.llm_model:
            raise ValueError("LLM_MODEL must not be empty")



def load_settings() -> Settings:
    settings = Settings(
        project_root=PROJECT_ROOT,
        raw_dir=_path_from_env("RAW_DIR", "raw"),
        wiki_dir=_path_from_env("WIKI_DIR", "wiki"),
        data_dir=_path_from_env("DATA_DIR", "data"),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ).strip(),
        similarity_threshold=_float_from_env("SIMILARITY_THRESHOLD", 0.68),
        top_k=_int_from_env("TOP_K", 5),
        llm_provider=os.getenv("LLM_PROVIDER", "groq").strip(),
        llm_model=os.getenv("LLM_MODEL", "llama-3.1-8b-instant").strip(),
    )
    settings.validate()
    return settings


settings = load_settings()
