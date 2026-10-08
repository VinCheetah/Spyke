from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from spyke.infrastructure.database.base import Base
from spyke.infrastructure.database.models import SourceDocumentModel
from spyke.infrastructure.sources.http import SourceHttpClient, SourceHttpError
from spyke.infrastructure.storage.archive import RawArchive
from spyke.infrastructure.storage.service import SourceArchiveService


def test_raw_archive_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    archive = RawArchive(tmp_path)

    first = archive.store(
        b"same body",
        source_system="ffvb",
        season="2025/2026",
        entity="LIIDF",
        category="calendars",
        suffix="json",
    )
    second = archive.store(
        b"same body",
        source_system="ffvb",
        season="2025/2026",
        entity="LIIDF",
        category="calendars",
        suffix="json",
    )

    assert first == second
    assert archive.read(first.storage_key) == b"same body"
    assert first.storage_key.startswith("ffvb/2025-2026/LIIDF/calendars/")
    assert first.storage_key.endswith(".json")
    assert len(list(tmp_path.rglob("*.json"))) == 1

    with pytest.raises(ValueError, match="inside the archive root"):
        archive.read("../../outside.bin")


def test_raw_archive_supports_binary_documents_without_trusting_path_input(tmp_path: Path) -> None:
    archive = RawArchive(tmp_path)

    stored = archive.store(
        b"%PDF-raw",
        source_system="fdme",
        season="2025/2026",
        entity="LIIDF",
        category="matches",
        suffix="pdf",
    )

    assert stored.storage_key.startswith("fdme/2025-2026/LIIDF/matches/")
    assert archive.read(stored.storage_key) == b"%PDF-raw"


def test_http_client_retries_transient_responses() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, content=b"{}", request=request)

    transport = httpx.MockTransport(handler)
    with SourceHttpClient(
        base_url="https://example.test", retries=1, transport=transport
    ) as client:
        document = client.fetch("/clubs")

    assert calls == 2
    assert document.body == b"{}"


def test_http_client_raises_after_retry_budget() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503, request=request))

    with (
        SourceHttpClient(base_url="https://example.test", retries=0, transport=transport) as client,
        pytest.raises(SourceHttpError),
    ):
        client.fetch("/clubs")


def test_source_archive_registers_one_document_per_hash(tmp_path: Path) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    response = httpx.Response(
        200,
        content=b"{}",
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://example.test/clubs"),
    )

    with Session(engine) as session:
        service = SourceArchiveService(tmp_path)
        first = service.archive_response(
            session,
            service_response(response),
            source_system="ffvb",
            season="2025/2026",
            entity="LIIDF",
            category="clubs",
            suffix="json",
        )
        second = service.archive_response(
            session,
            service_response(response),
            source_system="ffvb",
            season="2025/2026",
            entity="LIIDF",
            category="clubs",
            suffix="json",
        )
        session.commit()

        assert first.id == second.id
        assert session.query(SourceDocumentModel).count() == 1


def service_response(response: httpx.Response):
    from spyke.infrastructure.sources.http import HttpDocument

    return HttpDocument(
        url=str(response.request.url),
        body=response.content,
        status_code=response.status_code,
        content_type=response.headers.get("content-type"),
        etag=None,
        last_modified=None,
    )
