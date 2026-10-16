"""Commande CLI `spyke import` (pipeline unifié : scrape -> download -> parse)."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime, date as dt_date
from pathlib import Path
from typing import Optional, List

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from spyke.cli.args import AllEntitiesParam, EntityParam, LimitParam, SeasonParam, ForceParam, DryRunParam, VerboseParam, ArchiveModeParam
from spyke.application.imports.clubs import ClubsImporter
from spyke.cli.shared.output_formatting import max_show
from spyke.config import settings
from spyke.cli.shared.arg_resolver import resolve_seasons, resolve_entity_type
from spyke.domain.entities.organisation import Entity, Season
from spyke.domain.enums import ArchiveMode
from spyke.infrastructure.ffvb.dto import ClubRecord, EntityRecord


console = Console()

def debug():
    """
    Debug the import pipeline.
    """
    from spyke.infrastructure.ffvb.client import FfvbClient
    from spyke.application.imports.entities import EntitiesImporter
    from spyke.infrastructure.database.session import DatabaseSession
    seasons = None
    entities=["LIRA"]
    seasons: list[Season] = resolve_seasons(seasons or [])
    entities_list: list[str] = entities or []
    ffvb_client = FfvbClient()

    with DatabaseSession() as session:
        entities_importer = EntitiesImporter(session=session, client=ffvb_client)
        all_entities = False
        entities: list[EntityRecord] = entities_importer.get_filtered_entities(entities_list, all_entities)
        entities_importer.enrich_entities_codes(entities)
        entities_importer.enrich_entities(entities)


