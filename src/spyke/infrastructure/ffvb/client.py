import json
from functools import wraps
from typing import Any
from urllib.parse import urlencode

from spyke.config import settings
from spyke.domain.entities import Season
from spyke.domain.enums import ArchiveMode, Echelon, RawDataCategory
from spyke.infrastructure.ffvb.endpoints import FfvbEndpoints
from spyke.infrastructure.sources.http import HttpDocument, SourceHttpClient
from spyke.infrastructure.storage.service import ArchiveService


def archive(category: RawDataCategory):
    def decorator(func: Any) -> Any:
        @wraps(func)
        def wrapper(ffvb_client: "FfvbClient", *args, **kwargs) -> HttpDocument:
            params: dict[str, Any] = kwargs or {}
            service: ArchiveService = ArchiveService()
            match ffvb_client.archive_mode:
                case ArchiveMode.USE:
                    # Check if the document is already in the archive
                    document = service.load(params=params, category=category)
                    if document:
                        return document
                    else:
                        # Fetch the document and store it in the archive
                        document = func(ffvb_client, *args, **kwargs)
                        service.save(document=document, category=category, params=params)
                        return document
                case ArchiveMode.REFRESH:
                    # Fetch the document and store it in the archive, overwriting any existing entry
                    document = func(ffvb_client, *args, **kwargs)
                    service.save(document=document, category=category, params=params)
                    return document
                case ArchiveMode.OFFLINE:
                    # Attempt to retrieve the document from the archive, raise an error if not found
                    document = service.load(params=params, category=category)
                    if document:
                        return document
                    else:
                        raise ValueError(f"Document not found in archive for category {category}.")
                case ArchiveMode.DISABLED:
                    # Fetch the document without interacting with the archive
                    return func(ffvb_client, *args, **kwargs)
            return func(ffvb_client, *args, **kwargs)

        return wrapper

    return decorator


class FfvbClient:
    """Acquisition facade for FFVolley referential documents."""

    def __init__(
        self,
        http: SourceHttpClient | None = None,
        endpoints: FfvbEndpoints | None = None,
    ) -> None:
        self.http = http or SourceHttpClient(settings.ffvb_base_url)
        self.endpoints = endpoints or FfvbEndpoints()
        self.archive_mode: ArchiveMode = ArchiveMode.USE

    @archive(category=RawDataCategory.ENTITIES)
    def fetch_entities(self) -> HttpDocument:
        return self.http.fetch(self.endpoints.entities)

    @archive(category=RawDataCategory.CLUBS)
    def fetch_club(self, id_club: str) -> HttpDocument:
        """Fetch a club's information."""
        params = self.endpoints.entities_directory_params.copy()
        params["id_club"] = id_club
        return self.http.post(self.endpoints.clubs, params=params)

    @archive(category=RawDataCategory.ENTITIES_CODE)
    def fetch_entities_directory(self) -> HttpDocument:
        """Fetch the FFVB directory page listing all entities."""
        return self.http.post(
            self.endpoints.entities_directory,
            params=self.endpoints.entities_directory_params.copy(),
        )

    @archive(category=RawDataCategory.ENTITY)
    def fetch_entity_directory(self, entity_code: str, entity_type: Echelon) -> HttpDocument:
        """Fetch a league or committee directory page.

        ``entity_code`` is the numeric code used by the FFVB directory form
        """
        params = self.endpoints.entities_directory_params.copy()
        match entity_type:
            case Echelon.DEPARTEMENTAL:
                params["ws_new_comit"] = entity_code
            case Echelon.REGIONAL:
                params["ws_new_ligue"] = entity_code
            case _:
                raise ValueError(f"Unsupported entity type for directory fetch: {entity_type}")
        return self.http.post(self.endpoints.clubs, params=params)

    @archive(category=RawDataCategory.COMPETITIONS)
    def fetch_competitions(self, entity_code: str, season: Season) -> HttpDocument:
        params = {
            "saison": season.code,
            "codent": entity_code,
        }
        return self.http.fetch(self.endpoints.competitions, params=params)

    @archive(category=RawDataCategory.CALENDAR)
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
