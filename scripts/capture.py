"""Command-line interface for the SecondSelf capture pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from secondself.capture import CaptureError, get_default_store  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture notes, links, and files into SecondSelf raw/.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    note_parser = subparsers.add_parser("note", help="Capture a note")
    note_parser.add_argument("content", nargs="?", help="Note content")
    note_parser.add_argument("--stdin", action="store_true", help="Read note content from stdin")
    note_parser.add_argument("--file", type=Path, help="Read note content from a text file")
    note_parser.add_argument("--title", help="Optional note title")

    link_parser = subparsers.add_parser("link", help="Capture a URL")
    link_parser.add_argument("url", help="HTTP or HTTPS URL")
    link_parser.add_argument("--title", help="Optional link title")

    file_parser = subparsers.add_parser("file", help="Capture a file")
    file_parser.add_argument("path", type=Path, help="Path to the file")
    file_parser.add_argument("--title", help="Optional file title")

    return parser


def _note_content(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    selected_inputs = sum(bool(value) for value in (args.stdin, args.file, args.content is not None))
    if selected_inputs != 1:
        parser.error("note requires exactly one of content, --stdin, or --file")
    if args.stdin:
        return sys.stdin.read()
    if args.file:
        try:
            return args.file.read_text(encoding="utf-8")
        except OSError as exc:
            raise CaptureError(f"Unable to read note file: {args.file}") from exc
    return args.content


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = get_default_store()

    try:
        if args.command == "note":
            record = store.capture_note(_note_content(args, parser), title=args.title)
        elif args.command == "link":
            record = store.capture_link(args.url, title=args.title)
        else:
            record = store.capture_file(args.path, title=args.title)
    except (CaptureError, OSError) as exc:
        print(f"Capture failed: {exc}", file=sys.stderr)
        return 1

    print(f"Captured {record.type}: {record.id}")
    print(f"Metadata: {store.captures_dir / f'{record.id}.json'}")
    if record.file_path:
        print(f"Attachment: {store.raw_dir / record.file_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
