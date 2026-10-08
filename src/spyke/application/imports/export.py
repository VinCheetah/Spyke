from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from spyke.config import settings
from spyke.domain.entities import Season, Entity
from spyke.infrastructure.database.models import SourceDocumentModel
from spyke.infrastructure.ffvb.client import FfvbClient
from spyke.infrastructure.ffvb.export import ExportMatchRecord, FfvbCalendarExportParser
from spyke.infrastructure.storage.service import SourceArchiveService


@dataclass(frozen=True)
class ExportAcquisitionResult:
    """Archived FFVB export and its source-level parsed records."""

    document: SourceDocumentModel
    records: tuple[ExportMatchRecord, ...]


class FfvbExportAcquisition:
    """Acquire and parse the FFVB export without persisting canonical entities.

    Canonical persistence belongs to a later import step because the export's
    pool and competition mapping must be resolved before writing matches.
    """

    parser_version = "calendar-export-1"

    def __init__(
        self,
        session: Session,
        client: FfvbClient,
        archive_root: Path = settings.archive_dir,
        *,
        parser: FfvbCalendarExportParser | None = None,
    ) -> None:
        self.session = session
        self.client = client
        self.archive = SourceArchiveService(archive_root)
        self.parser = parser or FfvbCalendarExportParser()

    def acquire(
        self,
        *,
        entity: Entity,
        season: Season,
        pool_code: str | None = None,
    ) -> ExportAcquisitionResult:
        response = self.client.fetch_calendar_export(
            entity=entity,
            season=season,
            pool_code=pool_code,
        )
        document = self.archive.archive_response(
            self.session,
            response,
            source_system="ffvb",
            season=season,
            entity=entity,
            category="calendars",
            parser_type="ffvb-calendar-export",
            parser_version=self.parser_version,
            suffix="csv",
        )
        records = self.parser.parse(
            response.body,
            entity=entity,
            season=season,
            source_url=response.url,
        )
        self.session.commit()
        return ExportAcquisitionResult(document, tuple(records))
