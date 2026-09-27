import json
from typing import Any

from spyke.infrastructure.ffvb.endpoints import FfvbEndpoints
from spyke.infrastructure.sources.http import HttpDocument, SourceHttpClient


class FfvbClient:
    """Acquisition facade for FFVolley referential documents."""

    def __init__(self, http: SourceHttpClient, endpoints: FfvbEndpoints | None = None) -> None:
        self.http = http
        self.endpoints = endpoints or FfvbEndpoints()

    def fetch_leagues(self) -> HttpDocument:
        return self.http.fetch(self.endpoints.leagues)

    def fetch_clubs(self) -> HttpDocument:
        return self.http.fetch(self.endpoints.clubs)

    def fetch_competitions(self) -> HttpDocument:
        return self.http.fetch(self.endpoints.competitions)

    def fetch_calendar(self) -> HttpDocument:
        return self.http.fetch(self.endpoints.calendar)


def decode_json(document: HttpDocument) -> Any:
    """Decode a JSON source response with a source-specific error message."""
    try:
        return json.loads(document.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid JSON response from {document.url}") from error
