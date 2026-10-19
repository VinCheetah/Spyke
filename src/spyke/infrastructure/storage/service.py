"""Application service combining raw source storage and database metadata."""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Any

from spyke.config import settings
from spyke.domain.enums import RawDataCategory
from spyke.infrastructure.sources.http import HttpDocument

logger = logging.getLogger(__name__)


class ArchiveService:
    """Legacy document archive used by the FFVB client decorator.

    This API predates :class:`SourceArchiveService`; it remains binary-safe so
    callers using the older interface do not silently corrupt source documents.
    """

    archive_dir: Path

    def __init__(self, archive_dir: Path = settings.archive_dir) -> None:
        self.archive_dir = archive_dir.expanduser().resolve()
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        """Atomically replace a file with the supplied bytes."""
        path.parent.mkdir(parents=True, exist_ok=True)

        fd, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)

        try:
            with os.fdopen(fd, "wb") as file:
                file.write(data)
                file.flush()
                os.fsync(file.fileno())

            # Atomic when supported by the underlying filesystem.
            os.replace(temporary_path, path)

            # On POSIX, also request persistence of the directory entry.
            if os.name == "posix":
                directory_fd = os.open(
                    path.parent,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
                )
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)

        finally:
            # Clean up if writing or replacement failed.
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

    def save(
        self,
        *,
        document: HttpDocument,
        category: RawDataCategory,
        params: dict[str, Any] | None = None,
    ) -> None:
        # Ne jamais remplacer le cache avec une erreur HTTP.
        if not 200 <= document.status_code < 300 or document.status_code == 204:
            return None

        path = self.archive_dir / document.storage_key(category, params or {})

        content_type = document.content_type or ""
        mime = content_type.split(";")[0].strip().lower()
        extensions = {
            "text/html": ".html",
            "text/csv": ".csv",
            "application/pdf": ".pdf",
            "application/json": ".json",
            "text/plain": ".txt",
        }
        extension = extensions.get(mime) or mimetypes.guess_extension(mime)
        extension = extension or ".bin"

        body_path = path.with_suffix(extension)
        metadata_path = path.with_suffix(".json")

        # Put every document metadata
        metadata = {
            "url": document.url,
            "status_code": document.status_code,
            "content_type": document.content_type,
            "etag": document.etag,
            "params": document.params,
            "last_modified": document.last_modified,
            "body_file": body_path.name,
            "body_size": len(document.body),
            "body_sha256": hashlib.sha256(document.body).hexdigest(),
        }

        # Écrire le corps avant de publier les nouvelles métadonnées.
        self._atomic_write(body_path, document.body)
        self._atomic_write(
            metadata_path,
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8"),
        )

    def load(self, *, category: RawDataCategory, params: dict[str, Any]) -> HttpDocument | None:

        path = self.archive_dir / HttpDocument.build_storage_key(category, params)
        metadata_path = path.with_suffix(".json")
        if not metadata_path.exists():
            return None

        with open(metadata_path, "rb") as f:
            metadata = json.load(f)

        body_file = metadata.get("body_file")
        if not body_file:
            return None

        body_path = path.with_name(body_file)
        if not body_path.exists():
            return None

        with open(body_path, "rb") as f:
            body = f.read()

        return HttpDocument(
            url=metadata.get("url", ""),
            body=body,
            status_code=metadata.get("status_code", 0),
            content_type=metadata.get("content_type"),
            etag=metadata.get("etag"),
            params=metadata.get("params"),
            last_modified=metadata.get("last_modified"),
        )
