import json
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from spyke.application.imports.ffvb import FfvbReferentialImport
from spyke.infrastructure.database.base import Base
from spyke.infrastructure.database.models import ImportRunModel, SourceDocumentModel
from spyke.infrastructure.ffvb.client import FfvbClient
from spyke.infrastructure.sources.http import SourceHttpClient

PAYLOADS: dict[str, Any] = {
    "/leagues": {
        "leagues": [
            {
                "id": "league-1",
                "name": "Ligue test",
                "code": "TEST",
                "echelon": "REGIONAL",
            }
        ]
    },
    "/clubs": {
        "clubs": [
            {
                "id": "club-1",
                "name": "Club test",
                "code": "1234567",
                "league_id": "league-1",
            }
        ]
    },
    "/competitions": {
        "competitions": [
            {
                "id": "competition-1",
                "name": "R1 masculin",
                "code": "R1M",
                "season_start": 2025,
                "season_end": 2026,
                "organizer_id": "league-1",
                "gender": "MASCULIN",
                "category": "SENIOR",
                "echelon": "REGIONAL",
                "division": "REGIONALE_1",
            }
        ]
    },
    "/calendar": {"matches": []},
}


def test_ffvb_import_archives_each_response_and_completes_run(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=json.dumps(PAYLOADS[request.url.path]).encode(),
            headers={"content-type": "application/json"},
            request=request,
        )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    transport = httpx.MockTransport(handler)

    with Session(engine) as session:
        with SourceHttpClient(base_url="https://example.test", transport=transport) as http_client:
            result = FfvbReferentialImport(
                session,
                FfvbClient(http_client),
                tmp_path,
            ).run()

        run = session.query(ImportRunModel).one()
        assert run.status == "SUCCESS"
        assert result["leagues"].created == 1
        assert result["calendar"].seen == 0
        assert session.query(SourceDocumentModel).count() == 4
