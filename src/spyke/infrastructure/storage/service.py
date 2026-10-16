"""Application service combining raw source storage and database metadata."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from spyke.config import settings
from spyke.domain.entities import Entity, Season
from spyke.domain.enums import RawDataCategory
from spyke.infrastructure.database.models import SourceDocumentModel
from spyke.infrastructure.sources.http import HttpDocument, ParameterMapping
from spyke.infrastructure.storage.archive import RawArchive


class ArchiveService:
    """Legacy document archive used by the FFVB client decorator.

    This API predates :class:`SourceArchiveService`; it remains binary-safe so
    callers using the older interface do not silently corrupt source documents.
    """

    archive_dir: Path

    def __init__(self, archive_dir: Path = settings.archive_dir) -> None:
        self.archive_dir = archive_dir.expanduser().resolve()
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self, data_category: RawDataCategory, document: HttpDocument) -> None:
        storage_key = document.storage_key(data_category)
        path = self._resolve(storage_key)
        payload = {
            "url": document.url,
            "body": base64.b64encode(document.body).decode("ascii"),
            "status_code": document.status_code,
            "content_type": document.content_type,
            "etag": document.etag,
            "params": document.params,
            "sub_params": document.sub_params,
            "last_modified": document.last_modified,
        }
        self._write_json(path, payload)

    def retrieve(
        self,
        params: ParameterMapping,
        data_category: RawDataCategory,
    ) -> HttpDocument | None:
        storage_key = HttpDocument.build_storage_key(data_category, params)
        try:
            with self._resolve(storage_key).open(encoding="utf-8") as archive_file:
                data = json.load(archive_file)
        except FileNotFoundError:
            return None
        try:
            body = base64.b64decode(data["body"], validate=True)
            return HttpDocument(
                url=data["url"],
                body=body,
                status_code=data["status_code"],
                content_type=data.get("content_type"),
                etag=data.get("etag"),
                params=data.get("params", {}),
                sub_params=data.get("sub_params", {}),
                last_modified=data.get("last_modified"),
            )
        except (KeyError, TypeError, ValueError, binascii.Error) as error:
            raise ValueError(f"Invalid archived document: {storage_key}") from error

    def exists(self, storage_key: str) -> bool:
        try:
            return self._resolve(storage_key).is_file()
        except ValueError:
            return False

    def _resolve(self, storage_key: str) -> Path:
        path = (self.archive_dir / storage_key).resolve()
        try:
            path.relative_to(self.archive_dir)
        except ValueError as error:
            raise ValueError("storage key must resolve inside the archive root") from error
        return path

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as archive_file:
                json.dump(payload, archive_file, ensure_ascii=False, indent=2)
                archive_file.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


class SourceArchiveService:
    """Persist source responses as immutable files and database metadata."""

    def __init__(self, archive_root: Path = settings.archive_dir) -> None:
        self.archive = RawArchive(archive_root)

    def archive_response(
        self,
        session: Session,
        document: HttpDocument,
        *,
        source_system: str,
        season: str | Season,
        entity: str | Entity,
        category: str,
        parser_type: str | None = None,
        parser_version: str | None = None,
        suffix: str,
    ) -> SourceDocumentModel:
        """Archive a response and return one metadata row for its content hash."""
        body_hash = hashlib.sha256(document.body).hexdigest()
        existing = session.scalar(
            select(SourceDocumentModel).where(SourceDocumentModel.content_hash == body_hash)
        )
        stored = self.archive.store(
            document.body,
            source_system=source_system,
            season=str(season),
            entity=str(entity),
            category=category,
            suffix=suffix,
        )
        if existing is not None:
            return existing

        metadata = SourceDocumentModel(
            source_system=source_system,
            url=document.url,
            content_hash=body_hash,
            content_type=document.content_type,
            size=len(document.body),
            fetched_at=datetime.now(UTC),
            http_status=document.status_code,
            etag=document.etag,
            last_modified=document.last_modified,
            storage_key=stored.storage_key,
            parser_type=parser_type,
            parser_version=parser_version,
        )
        session.add(metadata)
        session.flush()
        return metadata
