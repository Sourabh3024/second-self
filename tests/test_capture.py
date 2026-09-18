import json
from pathlib import Path

import pytest

from secondself.capture import CaptureError, CaptureStore


def read_record(store: CaptureStore, capture_id: str) -> dict:
    path = store.captures_dir / f"{capture_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_capture_note_writes_immutable_metadata(tmp_path: Path) -> None:
    store = CaptureStore(tmp_path / "raw")

    record = store.capture_note("A useful idea\nwith more detail.")
    payload = read_record(store, record.id)

    assert record.type == "note"
    assert payload["id"] == record.id
    assert payload["content"] == "A useful idea\nwith more detail."
    assert payload["title"] == "A useful idea"
    assert payload["captured_at"]
    assert payload["status"] == "unprocessed"


def test_capture_link_validates_and_preserves_url(tmp_path: Path) -> None:
    store = CaptureStore(tmp_path / "raw")

    record = store.capture_link("https://example.com/article", title="Reference")
    payload = read_record(store, record.id)

    assert record.type == "link"
    assert payload["url"] == "https://example.com/article"
    assert payload["content"] == "https://example.com/article"
    assert payload["title"] == "Reference"

    with pytest.raises(CaptureError, match="valid http or https URL"):
        store.capture_link("example.com/article")


def test_capture_file_copies_attachment_and_records_checksum(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    source = tmp_path / "source file.txt"
    source.write_text("real file content", encoding="utf-8")
    store = CaptureStore(raw_dir)

    record = store.capture_file(source)
    payload = read_record(store, record.id)
    attachment = raw_dir / payload["file_path"]

    assert record.type == "file"
    assert attachment.is_file()
    assert attachment.read_text(encoding="utf-8") == "real file content"
    assert payload["original_filename"] == "source file.txt"
    assert payload["file_size"] == source.stat().st_size
    assert len(payload["sha256"]) == 64
    assert payload["file_path"].startswith("attachments/")


def test_capture_ids_are_unique(tmp_path: Path) -> None:
    store = CaptureStore(tmp_path / "raw")

    first = store.capture_note("first")
    second = store.capture_note("second")

    assert first.id != second.id
    assert (store.captures_dir / f"{first.id}.json").is_file()
    assert (store.captures_dir / f"{second.id}.json").is_file()


def test_empty_note_and_missing_file_are_rejected(tmp_path: Path) -> None:
    store = CaptureStore(tmp_path / "raw")

    with pytest.raises(CaptureError, match="must not be empty"):
        store.capture_note("   ")
    with pytest.raises(CaptureError, match="does not exist"):
        store.capture_file(tmp_path / "missing.pdf")
