from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from spyke.config import settings
from spyke.domain.entities.organisation import Season
from spyke.application.imports.referentials import ImportSummary, ReferentialImporter
from spyke.infrastructure.database.models import ImportRunModel
from spyke.infrastructure.ffvb.client import FfvbClient, decode_json
from spyke.infrastructure.ffvb.parsers import JsonReferentialParser
from spyke.infrastructure.sources.http import HttpDocument
from spyke.infrastructure.storage.service import SourceArchiveService

RecordT = TypeVar("RecordT")


class FfvbReferentialImport:
    """Orchestrate archive, parse and persistence for FFVolley referentials."""

    def __init__(
        self,
        session: Session,
        client: FfvbClient,
        archive_root: Path = settings.archive_dir,
        *,
        parser: JsonReferentialParser | None = None,
    ) -> None:
        self.session = session
        self.client = client
        self.archive = SourceArchiveService(archive_root)
        self.parser = parser or JsonReferentialParser()
        self.persistence = ReferentialImporter(session)

    def run(
        self,
        *,
        season: str = "unspecified",
        entity_code: str = "national",
    ) -> dict[str, ImportSummary]:
        run = ImportRunModel(
            source_system="ffvb",
            import_type="referentials",
            status="RUNNING",
            started_at=datetime.now(UTC),
        )
        self.session.add(run)
        self.session.commit()
        try:
            results = {
                "leagues": self._import_document(
                    self.client.fetch_leagues,
                    self.parser.leagues,
                    self.persistence.import_leagues,
                    season=season,
                    entity_code=entity_code,
                    category="leagues",
                ),
                "clubs": self._import_document(
                    self.client.fetch_clubs,
                    self.parser.clubs,
                    self.persistence.import_clubs,
                    season=season,
                    entity_code=entity_code,
                    category="clubs",
                ),
                "competitions": self._import_document(
                    self.client.fetch_competitions,
                    self.parser.competitions,
                    self.persistence.import_competitions,
                    season=season,
                    entity_code=entity_code,
                    category="competitions",
                ),
                "calendar": self._import_document(
                    self.client.fetch_calendar,
                    self.parser.calendar,
                    self.persistence.import_calendar,
                    season=season,
                    entity_code=entity_code,
                    category="calendars",
                ),
            }
            run.status = "SUCCESS"
            run.success_count = sum(result.created + result.updated for result in results.values())
            run.seen_count = sum(result.seen for result in results.values())
            run.finished_at = datetime.now(UTC)
            self.session.commit()
            return results
        except Exception:
            run.status = "FAILED"
            run.finished_at = datetime.now(UTC)
            self.session.commit()
            raise

    def _import_document(
        self,
        fetch: Callable[[], HttpDocument],
        parse: Callable[[Any], list[RecordT]],
        persist: Callable[[list[RecordT]], ImportSummary],
        *,
        season: str,
        entity_code: str,
        category: str,
    ) -> ImportSummary:
        response = fetch()
        self.archive.archive_response(
            self.session,
            response,
            source_system="ffvb",
            season=season,
            entity=entity_code,
            category=category,
            parser_type=parse.__qualname__,
            parser_version="referentials-1",
            suffix="json",
        )
        self.session.commit()
        payload = decode_json(response)
        return persist(parse(payload))
