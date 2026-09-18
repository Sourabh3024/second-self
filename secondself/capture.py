"""Capture notes, links, and files into the immutable raw store."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from secondself.config import settings


_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
_SUPPORTED_URL_SCHEMES = {"http", "https"}


class CaptureError(ValueError):
    """Raised when a capture cannot be validated or stored."""


@dataclass(frozen=True)
class CaptureRecord:
    id: str
    captured_at: str
    type: str
    source: str
    title: str
    content: str | None
    url: str | None
    file_path: str | None
    status: str
    original_filename: str | None = None
    file_size: int | None = None
    sha256: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _capture_id(captured_at: datetime) -> str:
    return f"cap_{captured_at:%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}"


def _safe_filename(name: str) -> str:
    candidate = Path(name).name
    candidate = _SAFE_FILENAME.sub("_", candidate).strip(" .")
    return candidate or "attachment"


def _default_title(content: str) -> str:
    first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
    return first_line[:80] or "Untitled note"


def _validate_url(url: str) -> None:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in _SUPPORTED_URL_SCHEMES or not parsed.netloc:
        raise CaptureError("URL must be a valid http or https URL")


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


class CaptureStore:
    """Write raw captures beneath a configured raw directory."""

    def __init__(self, raw_dir: Path | None = None) -> None:
        self.raw_dir = Path(raw_dir or settings.raw_dir)
        self.captures_dir = self.raw_dir / "captures"
        self.attachments_dir = self.raw_dir / "attachments"
        self.captures_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

    def _save_record(self, record: CaptureRecord) -> CaptureRecord:
        destination = self.captures_dir / f"{record.id}.json"
        if destination.exists():
            raise CaptureError(f"Capture ID collision: {record.id}")
        _write_json_atomic(destination, record.to_dict())
        return record

    def capture_note(
        self,
        content: str,
        *,
        title: str | None = None,
        source: str = "cli",
    ) -> CaptureRecord:
        if not content or not content.strip():
            raise CaptureError("Note content must not be empty")
        captured_at = _now()
        record = CaptureRecord(
            id=_capture_id(captured_at),
            captured_at=captured_at.isoformat(),
            type="note",
            source=source,
            title=(title or _default_title(content)).strip() or _default_title(content),
            content=content,
            url=None,
            file_path=None,
            status="unprocessed",
        )
        return self._save_record(record)

    def capture_link(
        self,
        url: str,
        *,
        title: str | None = None,
        source: str = "cli",
    ) -> CaptureRecord:
        normalized_url = url.strip()
        _validate_url(normalized_url)
        captured_at = _now()
        parsed = urlparse(normalized_url)
        fallback_title = parsed.netloc or normalized_url
        record = CaptureRecord(
            id=_capture_id(captured_at),
            captured_at=captured_at.isoformat(),
            type="link",
            source=source,
            title=(title or fallback_title).strip() or fallback_title,
            content=normalized_url,
            url=normalized_url,
            file_path=None,
            status="unprocessed",
        )
        return self._save_record(record)

    def capture_file(
        self,
        file_path: Path | str,
        *,
        title: str | None = None,
        source: str = "cli",
    ) -> CaptureRecord:
        source_path = Path(file_path).expanduser()
        if not source_path.is_file():
            raise CaptureError(f"File does not exist or is not a regular file: {source_path}")
        try:
            file_size = source_path.stat().st_size
        except OSError as exc:
            raise CaptureError(f"Unable to read file metadata: {source_path}") from exc

        captured_at = _now()
        capture_id = _capture_id(captured_at)
        attachment_name = f"{capture_id}_{_safe_filename(source_path.name)}"
        attachment_path = self.attachments_dir / attachment_name
        temporary_attachment = attachment_path.with_name(
            f".{attachment_path.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            shutil.copy2(source_path, temporary_attachment)
            digest = hashlib.sha256()
            with temporary_attachment.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            os.replace(temporary_attachment, attachment_path)
        except OSError as exc:
            temporary_attachment.unlink(missing_ok=True)
            attachment_path.unlink(missing_ok=True)
            raise CaptureError(f"Unable to copy file: {source_path}") from exc

        relative_path = attachment_path.relative_to(self.raw_dir).as_posix()
        record = CaptureRecord(
            id=capture_id,
            captured_at=captured_at.isoformat(),
            type="file",
            source=source,
            title=(title or source_path.stem).strip() or source_path.name,
            content=None,
            url=None,
            file_path=relative_path,
            status="unprocessed",
            original_filename=source_path.name,
            file_size=file_size,
            sha256=digest.hexdigest(),
        )
        try:
            return self._save_record(record)
        except Exception:
            attachment_path.unlink(missing_ok=True)
            raise


def get_default_store() -> CaptureStore:
    return CaptureStore()
