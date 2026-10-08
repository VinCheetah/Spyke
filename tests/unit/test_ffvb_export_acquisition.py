from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from spyke.application.imports.export import FfvbExportAcquisition
from spyke.infrastructure.database.base import Base
from spyke.infrastructure.database.models import SourceDocumentModel
from spyke.infrastructure.ffvb.client import FfvbClient
from spyke.infrastructure.sources.http import SourceHttpClient

EXPORT_BODY = (
    "Entité;Jo;Match;Date;Heure;EQA_no;EQA_nom;EQB_no;EQB_nom;Set;Score;Salle\n"
    "LIIDF;1;PMAA001;2026-01-10;20:00;0750001;AS VILLE;0590002;VB PARIS;3/1;"
    "25-20,21-25,25-22,25-18;Central\n"
).encode("latin-1")


def test_export_acquisition_archives_and_parses_real_source_shape(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("vbspo_calendrier_export.php")
        assert request.url.params["codent"] == "LIIDF"
        assert request.url.params["saison"] == "2025/2026"
        return httpx.Response(200, content=EXPORT_BODY, request=request)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with (
        Session(engine) as session,
        SourceHttpClient(
            base_url="https://www.ffvbbeach.org/ffvbapp/resu",
            transport=httpx.MockTransport(handler),
        ) as http,
    ):
        result = FfvbExportAcquisition(
            session,
            FfvbClient(http),
            tmp_path,
        ).acquire(entity_code="LIIDF", season="2025/2026")

        assert len(result.records) == 1
        assert result.records[0].match_code == "PMAA001"
        assert result.document.parser_version == "calendar-export-1"
        assert result.document.storage_key.startswith("ffvb/2025-2026/LIIDF/calendars/")
        assert session.query(SourceDocumentModel).count() == 1
