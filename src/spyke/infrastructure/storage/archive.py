"""Binary, content-addressed storage for source responses."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredArchive:
    """Location and identity of one archived payload."""

    storage_key: str
    content_hash: str
    size: int


class RawArchive:
    """Store immutable source payloads below a configured archive root."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def store(
        self,
        body: bytes,
        *,
        source_system: str,
        season: str,
        entity: str,
        category: str,
        suffix: str,
    ) -> StoredArchive:
        components = (
            self._safe_component(source_system),
            self._safe_component(season),
            self._safe_component(entity),
            self._safe_component(category),
        )
        safe_suffix = self._safe_suffix(suffix)
        content_hash = hashlib.sha256(body).hexdigest()
        storage_key = "/".join((*components, f"{content_hash}.{safe_suffix}"))
        destination = self._resolve(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            if not destination.is_file():
                raise ValueError(f"archive destination is not a file: {storage_key}")
        else:
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                dir=destination.parent,
            )
            try:
                with os.fdopen(fd, "wb") as temporary:
                    temporary.write(body)
                    temporary.flush()
                    os.fsync(temporary.fileno())
                os.replace(temporary_name, destination)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)

        return StoredArchive(storage_key, content_hash, len(body))

    def read(self, storage_key: str) -> bytes:
        """Read a stored payload, rejecting paths outside the archive root."""
        return self._resolve(storage_key).read_bytes()

    def _resolve(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise ValueError("storage key must resolve inside the archive root") from error
        return candidate

    @staticmethod
    def _safe_component(value: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())
        normalized = normalized.strip(".-")
        if not normalized or normalized in {".", ".."}:
            raise ValueError("archive path components must contain a visible name")
        return normalized

    @staticmethod
    def _safe_suffix(value: str) -> str:
        normalized = str(value).lstrip(".").lower()
        if not re.fullmatch(r"[a-z0-9]+", normalized):
            raise ValueError("archive suffix must contain only letters and digits")
        return normalized
