"""Commande CLI `spyke import` (pipeline unifié : scrape -> download -> parse)."""

from __future__ import annotations

from rich.console import Console

from spyke.cli.shared.arg_resolver import resolve_seasons
from spyke.domain.entities.organisation import Season
from spyke.infrastructure.ffvb.dto import EntityRecord

console = Console()


def debug():
    """
    Debug the import pipeline.
    """
    from spyke.application.imports.entities import EntitiesImporter
    from spyke.infrastructure.database.session import DatabaseSession
    from spyke.infrastructure.ffvb.client import FfvbClient

    seasons = None
    entities = ["LIRA"]
    seasons: list[Season] = resolve_seasons(seasons or [])
    entities_list: list[str] = entities or []
    ffvb_client = FfvbClient()

    with DatabaseSession() as session:
        entities_importer = EntitiesImporter(session=session, client=ffvb_client)
        all_entities = False
        entities: list[EntityRecord] = entities_importer.get_filtered_entities(entities_list, all_entities)
        entities_importer.enrich_entities_codes(entities)
        entities_importer.enrich_entities(entities)
