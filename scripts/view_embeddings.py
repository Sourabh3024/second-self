#!/usr/bin/env python3
"""Display embeddings saved in the project data folder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def resolve_embedding_path(path: str | None) -> Path:
    if path is None:
        project_root = Path(__file__).resolve().parents[1]
        return project_root / "data" / "embeddings" / "embeddings.npy"
    candidate = Path(path)
    if candidate.is_dir():
        return candidate / "embeddings.npy"
    return candidate


def load_payload(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Embedding file not found: {path}\n"
            "Expected a file like data/embeddings/embeddings.npy"
        )
    payload = np.load(path, allow_pickle=True)
    if isinstance(payload, np.ndarray) and payload.shape == () and payload.dtype == object:
        return payload.item()
    return payload


def print_payload(payload, show_full: bool = False):
    if isinstance(payload, np.ndarray):
        arr = np.asarray(payload)
        print(f"Array shape: {arr.shape}")
        print(f"Array dtype: {arr.dtype}")
        values = arr.flatten().tolist() if show_full else arr.flatten()[:8].tolist()
        print(f"Values: {values}")
        return

    if isinstance(payload, dict):
        print(f"Embedding count: {len(payload)}")
        print("Note ID\tDimensions\tValues")
        print("-------\t----------\t------")
        for key, value in payload.items():
            arr = np.asarray(value)
            values = arr.flatten().tolist() if show_full else arr.flatten()[:8].tolist()
            suffix = "" if show_full or arr.size <= 8 else " ..."
            print(f"{key}\t{arr.size}\t{values}{suffix}")
        return

    print(type(payload))
    print(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Display stored embeddings from the project data folder.")
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path to embeddings file or embeddings folder. Default: data/embeddings/embeddings.npy",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print every vector value instead of an eight-value preview.",
    )
    args = parser.parse_args()

    path = resolve_embedding_path(args.path)
    print(f"Loading embeddings from: {path}")

    try:
        payload = load_payload(path)
        index_path = path.parent / "index.json"
        if index_path.exists():
            metadata = json.loads(index_path.read_text(encoding="utf-8"))
            print(f"Embedding model: {metadata.get('embeddings_version', 'unknown')}")
            print(f"Similarity threshold: {metadata.get('threshold', 'unknown')}")
        print_payload(payload, show_full=args.full)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        print("If you want to inspect metadata too, check whether this exists:")
        print(str(path.parent / "index.json"))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
