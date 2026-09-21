"""Local embedding helpers for semantic similarity and note linking."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

SentenceTransformer = None


def lexical_similarity(left: str, right: str) -> float:
    def normalize(text: str) -> set[str]:
        tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
        stems: set[str] = set()
        for token in tokens:
            if token.endswith("ies") and len(token) > 4:
                stems.add(token[:-3] + "y")
            elif token.endswith("sses") and len(token) > 4:
                stems.add(token[:-2])
            elif token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
                stems.add(token[:-1])
            else:
                stems.add(token)
        return stems

    left_tokens = normalize(left)
    right_tokens = normalize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    common = len(left_tokens & right_tokens)
    if common == 0:
        return 0.0
    union = len(left_tokens | right_tokens)
    return float(common / union if union else 1.0)

from secondself.config import settings


_MODEL_CACHE: Any | None = None


def _fallback_vector(text: str) -> np.ndarray:
    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    vector = np.zeros(384, dtype=np.float32)
    if not tokens:
        return vector

    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1

    for token, weight in counts.items():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], byteorder="big", signed=False) % vector.shape[0]
        vector[index] += float(weight)

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector


def load_model() -> Any:
    raise RuntimeError("sentence-transformers is unavailable in this environment")


def embed_text(text: str) -> np.ndarray:
    return _fallback_vector(text)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def ensure_storage(data_dir: Path | None = None) -> Path:
    directory = Path(data_dir or settings.data_dir) / "embeddings"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def load_index(index_path: Path | None = None) -> dict[str, Any]:
    index_file = index_path or ensure_storage() / "index.json"
    if not index_file.exists():
        payload = {
            "records": {},
            "embeddings_version": settings.embedding_model,
            "threshold": settings.similarity_threshold,
        }
        index_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return json.loads(index_file.read_text(encoding="utf-8"))


def save_index(payload: dict[str, Any], index_path: Path | None = None) -> None:
    index_file = index_path or ensure_storage() / "index.json"
    index_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_embeddings(index_path: Path | None = None) -> dict[str, np.ndarray]:
    directory = Path(index_path).parent if index_path else ensure_storage()
    directory.mkdir(parents=True, exist_ok=True)
    vector_path = directory / "embeddings.npy"
    if not vector_path.exists():
        return {}
    try:
        payload = np.load(vector_path, allow_pickle=True).item()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_embeddings(vectors: dict[str, np.ndarray], index_path: Path | None = None) -> None:
    directory = Path(index_path).parent if index_path else ensure_storage()
    directory.mkdir(parents=True, exist_ok=True)
    vector_path = directory / "embeddings.npy"
    np.save(vector_path, vectors, allow_pickle=True)
    index = load_index(index_path)
    index["records"] = {
        key: {"shape": list(value.shape), "dtype": str(value.dtype)}
        for key, value in vectors.items()
    }
    save_index(index, index_path)
