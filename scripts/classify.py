"""Classify raw captures and write PARA wiki notes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from secondself.classify import Classifier, ClassificationError  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify raw captures into PARA wiki notes.")
    parser.add_argument("path", nargs="?", help="Optional path to a single capture JSON file")
    parser.add_argument("--all", action="store_true", help="Classify every unprocessed capture")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    classifier = Classifier()

    try:
        if args.path:
            result = classifier.process_capture(Path(args.path))
            print(f"Classified {result['id']} -> {result['category']} -> {result['wiki_path']}")
            return 0

        if args.all or not args.path:
            results = classifier.process_all()
            if not results:
                print("No unprocessed captures found.")
                return 0
            for result in results:
                print(f"Classified {result['id']} -> {result['category']} -> {result['wiki_path']}")
            return 0
    except (ClassificationError, OSError, ValueError) as exc:
        print(f"Classification failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
