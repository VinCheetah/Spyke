from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy.orm import Session

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
        archive_root: Path,
        *,
        parser: JsonReferentialParser | None = None,
    ) -> None:
        self.session = session
        self.client = client
        self.archive = SourceArchiveService(archive_root)
        self.parser = parser or JsonReferentialParser()
        self.persistence = ReferentialImporter(session)

    def run(self) -> dict[str, ImportSummary]:
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
                ),
                "clubs": self._import_document(
                    self.client.fetch_clubs,
                    self.parser.clubs,
                    self.persistence.import_clubs,
                ),
                "competitions": self._import_document(
                    self.client.fetch_competitions,
                    self.parser.competitions,
                    self.persistence.import_competitions,
                ),
                "calendar": self._import_document(
                    self.client.fetch_calendar,
                    self.parser.calendar,
                    self.persistence.import_calendar,
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
    ) -> ImportSummary:
        response = fetch()
        self.archive.archive_response(
            self.session,
            response,
            source_system="ffvb",
            parser_type=parse.__qualname__,
            parser_version="referentials-1",
            suffix="json",
        )
        self.session.commit()
        payload = decode_json(response)
        return persist(parse(payload))
