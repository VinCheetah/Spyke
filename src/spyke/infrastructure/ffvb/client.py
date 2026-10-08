import json
from typing import Any
from urllib.parse import urlencode

from spyke.infrastructure.ffvb.endpoints import FfvbEndpoints
from spyke.infrastructure.sources.http import HttpDocument, SourceHttpClient
from spyke.domain.entities import Season
from spyke.config import settings


class FfvbClient:
    """Acquisition facade for FFVolley referential documents."""

    def __init__(
        self, http: SourceHttpClient | None = None, endpoints: FfvbEndpoints | None = None
    ) -> None:
        self.http = http or SourceHttpClient(settings.ffvb_base_url)
        self.endpoints = endpoints or FfvbEndpoints()

    def fetch_entities(self) -> HttpDocument:
        return self.http.fetch(self.endpoints.entities)

    def fetch_club(self, club_id: str) -> HttpDocument:
        params = {"num_fede": club_id}
        return self.http.fetch(self.endpoints.clubs, params=params)

    def fetch_entity(self, entity_code: str) -> HttpDocument:
        params = {"LIGUE": entity_code}
        return self.http.fetch(self.endpoints.clubs, params=params)

    def fetch_competitions(self) -> HttpDocument:
        return self.http.fetch(self.endpoints.competitions)

    def fetch_calendar(self) -> HttpDocument:
        return self.http.fetch(self.endpoints.calendar)

    def fetch_calendar_export(
        self,
        entity_code: str,
        season: Season,
        pool_code: str | None = None,
    ) -> HttpDocument:
        """Fetch the structured FFVB calendar export for one entity."""
        params = {
            "saison": season.code,
            "codent": entity_code,
            "calend": "COMPLET",
        }
        if pool_code:
            params["poule"] = pool_code
        return self.http.fetch(self.endpoints.calendar_export, params=params)

    def match_sheet_url(self, entity_code: str, season: Season, match_code: str) -> str:
        """Build the canonical FFVB FDME URL for a discovered match."""
        query = urlencode({"saison": season.code, "codent": entity_code, "codmatch": match_code})
        return f"{self.http.base_url}{self.endpoints.match_sheet}?{query}"


def decode_json(document: HttpDocument) -> Any:
    """Decode a JSON source response with a source-specific error message."""
    try:
        return json.loads(document.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid JSON response from {document.url}") from error
