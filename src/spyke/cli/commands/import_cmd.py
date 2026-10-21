"""Commande CLI `spyke import` (pipeline unifié : scrape -> download -> parse)."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date as dt_date
from datetime import datetime
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

from spyke.application.imports.clubs import ClubsImporter
from spyke.application.imports.competitions import CompetitionImporter
from spyke.cli.args import (
    AllEntitiesParam,
    ArchiveModeParam,
    DryRunParam,
    EntityParam,
    ForceParam,
    LimitParam,
    SeasonParam,
    VerboseParam,
)
from spyke.cli.shared.arg_resolver import resolve_seasons
from spyke.cli.shared.output_formatting import max_show
from spyke.domain.entities.organisation import Season
from spyke.domain.enums import ArchiveMode
from spyke.infrastructure.ffvb.dto import ClubRecord, CompetitionRecord, EntityRecord

console = Console()

IMPORT_STEPS = ("entities", "clubs", "competitions", "calendar", "matches")


def format_duration(seconds: float) -> str:
    """Formate une durée de façon lisible, y compris pour les tâches rapides."""
    seconds = max(0.0, seconds)
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    total_seconds = int(seconds)
    minutes, remaining = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} h {minutes:02d} min {remaining:02d} s"
    if minutes:
        return f"{minutes} min {remaining:02d} s"
    return f"{remaining} s"


def format_rate(count: int, duration: float, unit: str) -> str:
    """Retourne une cadence stable et lisible, sans division par zéro."""
    if count <= 0 or duration <= 0:
        return f"0 {unit}/s"
    rate = count / duration
    if rate >= 100:
        value = f"{rate:.0f}"
    elif rate >= 10:
        value = f"{rate:.1f}"
    else:
        value = f"{rate:.2f}"
    return f"{value} {unit}/s"


class _RateColumn(ProgressColumn):
    """Colonne Rich affichant la cadence instantanée d'une tâche."""

    def render(self, task: Task) -> Text:
        rate = task.speed
        if rate is None or rate <= 0:
            return Text("—", style="dim cyan")
        return Text(f"{rate:.1f}/s", style="cyan")


@contextmanager
def make_progress(console: Console, *, refresh_per_second: float = 8) -> Iterator[Progress]:
    """Construit la présentation de progression commune à toutes les étapes."""
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        _RateColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        refresh_per_second=refresh_per_second,
        transient=False,
    )
    with progress:
        yield progress


@dataclass(slots=True)
class PipelineSubStep:
    """Mesure d'une sous-étape du pipeline d'importation."""

    stage: str
    key: str
    label: str
    duration: float
    items_count: int = 0
    items_unit: str = "éléments"


@dataclass(slots=True)
class PipelineTimer:
    """Collecte les métriques des étapes et affiche un bilan final homogène."""

    started_at: float = field(default_factory=time.perf_counter)
    sub_steps: list[PipelineSubStep] = field(default_factory=list)

    def record_sub_step(
        self,
        stage: str,
        key: str,
        label: str,
        duration: float,
        *,
        items_count: int = 0,
        items_unit: str = "éléments",
    ) -> None:
        self.sub_steps.append(
            PipelineSubStep(
                stage=stage,
                key=key,
                label=label,
                duration=max(0.0, duration),
                items_count=max(0, items_count),
                items_unit=items_unit,
            )
        )

    @property
    def duration(self) -> float:
        return time.perf_counter() - self.started_at

    def render_summary(self, output: Console = console) -> None:
        """Affiche les durées et cadences réellement mesurées."""
        if not self.sub_steps:
            return
        table = Table(box=box.SIMPLE_HEAVY, expand=True)
        table.add_column("Étape", style="bold cyan")
        table.add_column("Durée", justify="right")
        table.add_column("Volume", justify="right")
        table.add_column("Cadence", justify="right", style="green")
        for step in self.sub_steps:
            volume = f"{step.items_count} {step.items_unit}" if step.items_count else "—"
            rate = format_rate(step.items_count, step.duration, step.items_unit)
            table.add_row(step.label, format_duration(step.duration), volume, rate)
        table.add_row(
            "[bold]Total pipeline[/bold]",
            f"[bold]{format_duration(self.duration)}[/bold]",
            "",
            "",
        )
        output.print(
            Panel(
                table,
                title="[bold green]✓ Bilan de l'importation[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )


def import_data(
    entities: EntityParam = [],
    seasons: SeasonParam = [],
    all_entities: AllEntitiesParam = False,
    limit: LimitParam = None,
    force: ForceParam = False,
    dry_run: DryRunParam = False,
    archive_mode: ArchiveModeParam = ArchiveMode.USE,
    verbose: VerboseParam = False,
):
    """
    ...
    """
    from spyke.application.imports.entities import EntitiesImporter
    from spyke.infrastructure.database.session import DatabaseSession
    from spyke.infrastructure.ffvb.client import FfvbClient

    timer = PipelineTimer()
    seasons: list[Season] = resolve_seasons(seasons or [])
    entities_list: list[str] = entities or []
    render_config_panel(console, entities_list, seasons, list(IMPORT_STEPS), limit, dry_run, force)
    ffvb_client = FfvbClient()

    with DatabaseSession() as session:
        entities_importer = EntitiesImporter(session=session, client=ffvb_client)
        step_started = time.perf_counter()
        entities: list[EntityRecord] = entities_importer.get_filtered_entities(entities_list, all_entities)
        entities_importer.enrich_entities_codes(entities)
        entities_importer.enrich_entities(entities)
        timer.record_sub_step(
            "referentials",
            "entities",
            "Entités FFVB",
            time.perf_counter() - step_started,
            items_count=len(entities),
            items_unit="entités",
        )
        # entities_importer.import_records(entities)

        club_importer = ClubsImporter(session=session, client=ffvb_client)
        step_started = time.perf_counter()
        clubs: list[ClubRecord] = club_importer.get_clubs(ffvb_client, entities)
        timer.record_sub_step(
            "referentials",
            "clubs",
            "Clubs FFVB",
            time.perf_counter() - step_started,
            items_count=len(clubs),
            items_unit="clubs",
        )
        # club_importer.import_records(clubs)

        competition_importer = CompetitionImporter(session=session, client=ffvb_client)
        step_started = time.perf_counter()
        competitions: list[CompetitionRecord] = competition_importer.get_competitions(
            entities=entities, seasons=seasons
        )
        timer.record_sub_step(
            "referentials",
            "competitions",
            "Compétitions FFVB",
            time.perf_counter() - step_started,
            items_count=len(competitions),
            items_unit="compétitions",
        )

    timer.render_summary(console)


def render_config_panel(
    console: Console,
    entities: list[str],
    saisons: list[Season],
    steps: list[str],
    limit: int | None,
    dry_run: bool,
    refresh_cache: bool,
) -> None:
    """Affiche le panneau de configuration du pipeline."""
    entities_display = max_show(list(map(str, entities)))
    saisons_display = max_show(list(map(str, saisons)))

    config_grid = Table.grid(padding=(0, 2))
    config_grid.add_column(style="bold cyan", justify="right")
    config_grid.add_column(style="white")
    config_grid.add_column(style="bold cyan", justify="right")
    config_grid.add_column(style="white")

    pipeline_steps_display = "  →  ".join(
        f"[bold cyan]{s.upper()}[/bold cyan]" if s in steps else f"[dim]{s.upper()}[/dim]"
        for s in ["scrape", "download", "parse"]
    )
    config_grid.add_row(
        "Pipeline :",
        pipeline_steps_display,
        "Mode :",
        "[yellow]Aperçu (dry-run)[/yellow]" if dry_run else "[bold green]Exécution[/bold green]",
    )
    config_grid.add_row(
        "Saison(s) :",
        f"[cyan]{saisons_display}[/cyan]",
        "Limite :",
        f"[cyan]{limit or 'aucune'}[/cyan]",
    )
    config_grid.add_row(
        "Entité(s) :",
        f"[cyan]{entities_display or 'depuis la base'}[/cyan] [dim]({len(entities)} au total)[/dim]",
    )
    options_summary: list[str] = []
    config_grid.add_row(
        "Options :",
        f"[dim]{', '.join(options_summary) or 'défaut'}[/dim]",
        "Cache :",
        "[yellow]Rafraîchissement forcé[/yellow]" if refresh_cache else "[dim]Actif (exports CSV)[/dim]",
    )

    console.print(
        Panel(
            config_grid,
            title="[bold cyan]⚡ PyVolley[/bold cyan] · [bold white]Pipeline d'Importation FFVB[/bold white]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )


def _import_scrape(
    scraper,
    entities: list[str],
    saisons: list[str],
    *,
    verbose: bool = False,
    force_club_enrichment: bool = False,
    enrich_clubs: bool = True,
    geocode: bool = True,
    refresh_cache: bool = False,
    timer: PipelineTimer | None = None,
) -> None:
    """Étape 1 : scrape des exports CSV et import en base."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from spyke.infrastructure.database.connection import DatabaseSession
    from spyke.ingestion.importers.calendar_importer import CalendarImporter
    from spyke.scrapers.ffvb.export_scraper import get_unique_poules

    t_scrape_start = time.perf_counter()
    total_imported = 0
    total_updated = 0
    total_duplicates = 0
    total_clubs_created = 0
    total_clubs_enriched = 0
    total_clubs_uptodate = 0

    poules_by_entity: dict[str, set[str]] = {}
    saisons_by_entity: dict[str, set[str]] = {}

    def _process_export(target_entity: str, target_saison: str, export_data: list) -> None:
        nonlocal total_imported, total_updated, total_duplicates
        if not export_data:
            console.print(
                f"  [cyan]●[/cyan] [bold]{target_entity}[/bold] [dim]({target_saison})[/dim] : [yellow]aucun match trouvé[/yellow]"
            )
            return

        played = sum(1 for m in export_data if m.match_joue)
        poules = get_unique_poules(export_data)

        poule_codes = {(m.poule_code_ffvb or m.poule_code) for m in export_data if (m.poule_code_ffvb or m.poule_code)}
        if poule_codes:
            poules_by_entity.setdefault(target_entity, set()).update(poule_codes)
        saisons_by_entity.setdefault(target_entity, set()).add(target_saison)

        with DatabaseSession() as session:
            importer = CalendarImporter(session=session)
            if hasattr(importer, "import_matches"):
                result = importer.import_matches(export_data, target_entity, target_saison)
                matches = result.get("matches", []) if isinstance(result, dict) else result
                imported = result.get("imported", 0) if isinstance(result, dict) else len(matches)
                updated = result.get("updated", 0) if isinstance(result, dict) else 0
            else:
                matches = importer.sync_entity_matches(
                    target_entity,
                    parsed_matches=export_data,
                )
                imported = importer.stats.matches_created
                updated = importer.stats.matches_updated
            dup = max(0, len(export_data) - len(matches))
            total_imported += imported
            total_updated += updated
            total_duplicates += dup

            parts = []
            if imported:
                parts.append(f"[green]+{imported} créés[/green]")
            if updated:
                parts.append(f"[cyan]~{updated} mis à jour[/cyan]")
            if dup:
                parts.append(f"[dim]{dup} inchangés[/dim]")
            db_summary = " · ".join(parts) or "[dim]inchangé[/dim]"

            console.print(
                f"  [cyan]●[/cyan] [bold]{target_entity}[/bold] [dim]({target_saison})[/dim] : "
                f"[green]✓ {len(export_data)} matchs[/green] [dim]({played} joués, {len(poules)} poules)[/dim] "
                f"[dim]→[/dim] {db_summary}"
            )
            session.commit()

    tasks = [(target_entity, target_saison) for target_saison in saisons for target_entity in entities]
    scrape_kwargs = {"force_refresh": refresh_cache} if refresh_cache else {}

    t_csv_start = time.perf_counter()
    if len(tasks) > 1:
        max_workers = min(8, len(tasks))
        console.print(f"  [dim]Téléchargement parallèle de {len(tasks)} exports ({max_workers} workers)...[/dim]")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(scraper.scrape_entity, ent, sais, **scrape_kwargs): (ent, sais) for ent, sais in tasks
            }
            for future in as_completed(future_to_task):
                ent, sais = future_to_task[future]
                try:
                    export_data = future.result()
                except Exception as e:
                    console.print(f"  [cyan]●[/cyan] [bold]{ent}[/bold] [dim]({sais})[/dim] : [red]Erreur : {e}[/red]")
                    continue
                try:
                    _process_export(ent, sais, export_data)
                except Exception as e:
                    console.print(
                        f"  [cyan]●[/cyan] [bold]{ent}[/bold] [dim]({sais})[/dim] : [red]Erreur import base : {e}[/red]"
                    )
    else:
        for target_entity, target_saison in tasks:
            try:
                with console.status(f"[bold cyan]Récupération export CSV pour {target_entity} ({target_saison})..."):
                    export_data = scraper.scrape_entity(target_entity, target_saison, **scrape_kwargs)
            except Exception as e:
                console.print(
                    f"  [cyan]●[/cyan] [bold]{target_entity}[/bold] [dim]({target_saison})[/dim] : [red]Erreur : {e}[/red]"
                )
                continue
            try:
                _process_export(target_entity, target_saison, export_data)
            except Exception as e:
                console.print(
                    f"  [cyan]●[/cyan] [bold]{target_entity}[/bold] [dim]({target_saison})[/dim] : [red]Erreur import base : {e}[/red]"
                )
    csv_duration = time.perf_counter() - t_csv_start

    # ── Synchronisation canonique des clubs à la fin du scrape ──────────
    clubs_duration = 0.0
    if enrich_clubs and poules_by_entity:
        t_clubs_start = time.perf_counter()
        console.print()
        console.rule(
            "[bold magenta]Actualisation des clubs & salles (adressier FFVB)[/bold magenta]",
            style="magenta dim",
        )

        latest_saison = saisons[-1] if saisons else "2024/2025"
        with DatabaseSession() as session:
            if hasattr(CalendarImporter, "enrich_clubs"):
                from spyke.scrapers.ffvb.adressier_scraper import fetch_adressier

                for target_entity, target_poules in poules_by_entity.items():
                    fetch_adressier(
                        scraper.client,
                        scraper.base_url,
                        target_entity,
                        latest_saison,
                        sorted(target_poules),
                    )
                session.commit()
                entities_processed_clubs = len(poules_by_entity)
                clubs_duration = time.perf_counter() - t_clubs_start
                console.print(f"  [magenta]✓ Bilan clubs ({entities_processed_clubs} synchronisation)[/magenta]")
                return

            from spyke.ingestion import IngestionOrchestrator

            orchestrator = IngestionOrchestrator(session=session, saison=latest_saison)
            before = orchestrator.ctx.stats.to_dict()
            orchestrator.run_clubs(
                geocode=geocode,
                fetch_details=True,
                force_refresh=refresh_cache,
                max_workers=10,
            )
            session.commit()
            after = orchestrator.ctx.stats.to_dict()
            total_clubs_created = after["clubs_created"] - before["clubs_created"]
            total_clubs_enriched = after["clubs_updated"] - before["clubs_updated"]
            entities_processed_clubs = 1

        clubs_duration = time.perf_counter() - t_clubs_start
        console.print(
            f"  [magenta]✓ Bilan clubs ({entities_processed_clubs} synchronisation)[/magenta] : "
            f"[green]+{total_clubs_created} créés[/green] · "
            f"[cyan]~{total_clubs_enriched} mis à jour[/cyan] · "
            f"[dim]{total_clubs_uptodate} déjà à jour[/dim]"
        )

    total_scrape_duration = time.perf_counter() - t_scrape_start
    total_processed = total_imported + total_updated + total_duplicates
    rate_str = format_rate(total_processed, total_scrape_duration, "matchs")

    console.print(
        f"\n[green]✓ Scrape terminé en {format_duration(total_scrape_duration)} : "
        f"{total_imported} créés, {total_updated} mis à jour, {total_duplicates} inchangés "
        f"({total_processed} matchs au total, {rate_str})[/green]"
    )

    if timer:
        timer.record_sub_step(
            "scrape",
            "csv_import",
            "Téléchargement & Import CSV",
            csv_duration,
            items_count=total_processed,
            items_unit="matchs",
        )
        if enrich_clubs and poules_by_entity:
            timer.record_sub_step(
                "scrape",
                "clubs_enrich",
                "Actualisation Clubs & Salles",
                clubs_duration,
                items_count=total_clubs_created + total_clubs_enriched,
                items_unit="clubs",
            )


def _import_download(
    *,
    limit: int | None = None,
    saison: list[str] | None = None,
    entity: list[str] | None = None,
    concurrent: int = 5,
    verbose: bool = False,
    verify_existing: bool = False,
    delay: float | None = None,
    timer: PipelineTimer | None = None,
) -> None:
    """Étape 2 : téléchargement concurrent des PDFs.

    Procède en trois phases :
    1. Prépare la liste des téléchargements (marque les existants)
    2. Télécharge les fichiers manquants (async concurrent)
    3. Met à jour la base de données en batch
    """
    from spyke.infrastructure.database.connection import DatabaseSession, init_db
    from spyke.infrastructure.database.tables import CompetitionDB, MatchDB
    from sqlalchemy import or_, select
    from sqlalchemy.orm import joinedload

    init_db()
    today = dt_date.today()
    t_dl_start = time.perf_counter()

    # Phase 1 : préparer les téléchargements
    download_tasks: list[tuple[int, str, Path]] = []
    already_present: list[tuple[int, str]] = []  # (match_id, pdf_path)
    forced_redownload = {
        "invalid-local-pdf": 0,
        "downloaded-before-match-date": 0,
    }

    status_filter = ["discovered", "downloaded", "error"] if verify_existing else ["discovered", "error"]

    with DatabaseSession() as session:
        stmt = (
            select(MatchDB)
            .options(joinedload(MatchDB.saison))
            .options(joinedload(MatchDB.competition).joinedload(CompetitionDB.entite))
            .options(joinedload(MatchDB.poule))
            .where(
                MatchDB.match_joue == True,  # noqa: E712
                MatchDB.source_url.isnot(None),
                MatchDB.parsing_status.in_(status_filter),
                or_(
                    MatchDB.date_match.is_(None),
                    MatchDB.date_match <= today,
                ),
            )
        )
        stmt, _ = add_saison_filter(session, stmt, saison)
        stmt = add_entity_filter(session, stmt, entity)
        stmt = stmt.order_by(MatchDB.code_match)
        if limit:
            stmt = stmt.limit(limit)
        matches = list(session.scalars(stmt).all())

        if not matches:
            console.print("  [yellow]Aucun match à télécharger[/yellow]")
            return

        if verbose:
            console.print("  [dim]Mode verbeux: affichage des URLs, des skips et des erreurs de téléchargement.[/dim]")

        pdf_base = Path("data/pdfs")

        for match_db in matches:
            if not match_db.source_url:
                continue

            saison_code = match_db.saison.code if match_db.saison else "unknown"

            entite_code = getattr(
                getattr(match_db.competition, "entite", None),
                "code",
                None,
            )
            poule_code = getattr(match_db.poule, "code", None)
            dest_file = build_pdf_storage_path(
                pdf_base,
                saison_code=saison_code,
                entite_code=entite_code,
                poule_code=poule_code,
                match_code=match_db.code_match,
                journee=match_db.journee,
                unique_hint=match_db.id,
            )

            # Vérifier si déjà présent en O(1)
            existing = None
            if dest_file.exists():
                existing = dest_file
            else:
                existing = find_pdf_for_match(
                    match_db,
                    pdf_base,
                    saison_code=saison_code,
                )

            if existing:
                redownload_reason = (
                    _get_pdf_redownload_reason(match_db, existing, today=today) if verify_existing else None
                )
                if redownload_reason is None:
                    already_present.append((match_db.id, str(existing)))
                    if verbose:
                        console.print(f"  [dim]↷ {match_db.code_match} déjà présent: {existing}[/dim]")
                    continue

                forced_redownload[redownload_reason] += 1
                if verbose:
                    console.print(
                        f"  [yellow]↻ {match_db.code_match} retéléchargement forcé: {redownload_reason}[/yellow]"
                    )
                try:
                    existing.unlink()
                except OSError:
                    # Non bloquant: le téléchargement écrira la nouvelle cible.
                    pass

            download_tasks.append((match_db.id, match_db.source_url, dest_file))
            if verbose:
                console.print(f"  [dim]→ {match_db.code_match} | {match_db.source_url} -> {dest_file}[/dim]")

        # Mettre à jour les matchs dont le PDF existe déjà
        if already_present:
            matches_by_id = {m.id: m for m in matches}
            for match_id, pdf_path in already_present:
                m = matches_by_id.get(match_id)
                if m:
                    m.parsing_status = "downloaded"
                    m.source_pdf = pdf_path
            session.commit()

        forced_total = sum(forced_redownload.values())
        forced_msg = ""
        if forced_total:
            details = []
            if forced_redownload["invalid-local-pdf"]:
                details.append(f"{forced_redownload['invalid-local-pdf']} invalides")
            if forced_redownload["downloaded-before-match-date"]:
                details.append(f"{forced_redownload['downloaded-before-match-date']} antérieurs à la date du match")
            forced_msg = "  [dim]↻ Retéléchargement forcé : " + ", ".join(details) + "[/dim]"

        console.print(
            f"  [blue]●[/blue] Matchs ciblés : [bold]{len(matches)}[/bold]  [dim]│[/dim]  "
            f"Déjà présents : [green]{len(already_present)}[/green]  [dim]│[/dim]  "
            f"À télécharger : [cyan]{len(download_tasks)}[/cyan]"
        )
        if forced_msg:
            console.print(forced_msg)

    phase1_duration = time.perf_counter() - t_dl_start

    if not download_tasks:
        if timer:
            timer.record_sub_step(
                "download",
                "local_check",
                "Vérification locale des PDFs",
                phase1_duration,
                items_count=len(matches),
                items_unit="fichiers",
            )
        return

    # Phase 2 : téléchargement concurrent (pas d'accès DB ici)
    dl_results: list[tuple[int, Path, bool, str]] = []
    t_p2_start = time.perf_counter()

    async def _run():
        from spyke.infrastructure.http.async_http_client import AsyncHttpClient

        effective_delay = delay if delay is not None else 0.0
        async with AsyncHttpClient(
            request_delay=effective_delay,
            max_concurrent=concurrent,
            burst=concurrent,
        ) as client:
            with make_progress(console, refresh_per_second=8) as progress:
                task_id = progress.add_task(
                    "[cyan]Téléchargement des feuilles PDF...[/cyan]",
                    total=len(download_tasks),
                )

                async def _dl_one(match_id: int, url: str, dest: Path):
                    try:
                        response = await client.get(url)
                        content = response.content
                        if not content[:5].startswith(b"%PDF"):
                            raise ValueError("Réponse non-PDF")
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with open(dest, "wb") as f:
                            f.write(content)
                        dl_results.append((match_id, dest, True, ""))
                        progress.advance(task_id, 1)
                    except Exception as e:
                        error_msg = str(e)[:200]
                        dl_results.append((match_id, dest, False, error_msg))
                        if verbose:
                            progress.console.print(f"  [red]✗ {dest.stem}: {error_msg}[/red]")
                        progress.advance(task_id, 1)

                await asyncio.gather(*[_dl_one(mid, url, d) for mid, url, d in download_tasks])

    asyncio.run(_run())
    phase2_duration = time.perf_counter() - t_p2_start

    # Phase 3 : mise à jour DB en batch
    t_p3_start = time.perf_counter()
    downloaded = 0
    failed = 0

    batch_size = 200
    with DatabaseSession() as session:
        for i in range(0, len(dl_results), batch_size):
            chunk = dl_results[i : i + batch_size]
            chunk_ids = [mid for mid, _, _, _ in chunk]
            matches_chunk = {m.id: m for m in session.scalars(select(MatchDB).where(MatchDB.id.in_(chunk_ids))).all()}
            for match_id, dest, success, error_msg in chunk:
                m = matches_chunk.get(match_id)
                if not m:
                    continue
                if success:
                    m.parsing_status = "downloaded"
                    m.source_pdf = str(dest)
                    downloaded += 1
                else:
                    m.parsing_status = "error"
                    m.remarques = f"Download: {error_msg}"
                    failed += 1

            try:
                session.commit()
            except Exception:
                session.rollback()

    phase3_duration = time.perf_counter() - t_p3_start
    total_dl_duration = time.perf_counter() - t_dl_start
    dl_rate = format_rate(downloaded, phase2_duration, "PDFs")

    console.print(
        f"\n[green]✓ {downloaded} téléchargés en {format_duration(total_dl_duration)} ({dl_rate})[/green]"
        + (f" [dim]│ {len(already_present)} déjà présents[/dim]" if already_present else "")
        + (f" [dim]│[/dim] [red]{failed} erreurs[/red]" if failed else "")
    )
    if verbose and failed:
        console.print("  [bold red]Détails des erreurs de téléchargement :[/bold red]")
        for match_id, dest, success, error_msg in dl_results:
            if not success:
                console.print(f"  [red]✗ {dest.stem}: {error_msg}[/red]")

    if timer:
        timer.record_sub_step(
            "download",
            "local_check",
            "Vérification locale des PDFs",
            phase1_duration,
            items_count=len(matches),
            items_unit="fichiers",
        )
        timer.record_sub_step(
            "download",
            "async_fetch",
            "Téléchargement réseau concurrent",
            phase2_duration,
            items_count=downloaded,
            items_unit="PDFs",
        )
        timer.record_sub_step(
            "download",
            "db_update",
            "Mise à jour des statuts en base",
            phase3_duration,
            items_count=downloaded + failed,
            items_unit="matchs",
        )


def _import_parse(
    *,
    limit: int | None = None,
    saison: list[str] | None = None,
    entity: list[str] | None = None,
    force: bool = False,
    verbose: bool = False,
    plausibility: bool = True,
    plausibility_policy: str = "auto",
    review_fixes: bool = False,
    parser_name: str = "FastMatchSheetParser",
    rollup: bool = True,
    defer_player_stats: bool = True,
    timer: PipelineTimer | None = None,
) -> None:
    """Étape 3 : parsing des PDFs et enrichissement de la base."""
    from spyke.infrastructure.database.connection import DatabaseSession, init_db, sqlite_bulk_mode
    from spyke.infrastructure.database.tables import (
        CompetitionDB,
        EntiteFFVBDB,
        ImportLogDB,
        MatchDB,
        PouleDB,
        SaisonDB,
    )
    from spyke.ingestion import IngestionOrchestrator
    from spyke.parsers.fdme.factory import ParserFactory
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    init_db()
    t_parse_start = time.perf_counter()
    statuses = ["downloaded"]
    if force:
        statuses.extend(["parsed", "error"])

    parser = ParserFactory.get(parser_name)
    approval_cb = None
    if review_fixes:
        approval_cb = build_plausibility_reviewer(console)
    _configure_parser_plausibility(
        parser,
        enabled=plausibility,
        policy=plausibility_policy,
        approval=approval_cb,
    )

    with DatabaseSession() as session:
        stmt = (
            select(
                MatchDB.id,
                MatchDB.code_match,
                MatchDB.source_pdf,
                MatchDB.journee,
                SaisonDB.code.label("saison_code"),
                EntiteFFVBDB.code.label("entite_code"),
                PouleDB.code.label("poule_code"),
            )
            .join(MatchDB.saison, isouter=True)
            .join(MatchDB.competition, isouter=True)
            .join(CompetitionDB.entite, isouter=True)
            .join(MatchDB.poule, isouter=True)
            .where(
                MatchDB.parsing_status.in_(statuses),
                MatchDB.match_joue == True,  # noqa: E712
            )
        )
        stmt, saison_ids = add_saison_filter(session, stmt, saison)
        if saison_ids is not None and not saison_ids:
            console.print("[yellow]Aucune saison trouvée[/yellow]")
            return
        stmt = add_entity_filter(session, stmt, entity)
        stmt = stmt.order_by(MatchDB.code_match)
        if limit:
            stmt = stmt.limit(limit)
        matches_db = list(session.execute(stmt).all())

    if not matches_db:
        console.print(f"[yellow]Aucun match à parser (statuts : {', '.join(statuses)})[/yellow]")
        return

    # Localiser les PDFs (résolution directe O(1) d'abord, sans glob disque global)
    pdf_base = Path("data/pdfs")
    pdf_index = None

    match_pdf_pairs = []
    missing_matches = []
    for m in matches_db:
        pdf_path = find_pdf_for_match(m, pdf_base, pdf_index)
        if pdf_path:
            match_pdf_pairs.append((m.id, pdf_path))
        else:
            missing_matches.append(m)

    # Si certains fichiers ne sont pas trouvés aux chemins standard,
    # on indexe de manière ciblée uniquement la/les saison(s) concernée(s).
    if missing_matches:
        needed_saisons = set()
        if saison:
            from spyke.cli.helpers import normaliser_saison

            needed_saisons.update({normaliser_saison(s) for s in saison if s})
        else:
            needed_saisons.update(
                {getattr(m, "saison_code", None) for m in missing_matches if getattr(m, "saison_code", None)}
            )

        for s_code in needed_saisons:
            if s_code:
                seasonal_idx = build_pdf_index(pdf_base, saison_filter=s_code)
                if seasonal_idx:
                    if pdf_index is None:
                        pdf_index = {}
                    pdf_index.update(seasonal_idx)

        for m in missing_matches:
            pdf_path = find_pdf_for_match(m, pdf_base, pdf_index)
            if pdf_path:
                match_pdf_pairs.append((m.id, pdf_path))

    missing_pdf_count = len(matches_db) - len(match_pdf_pairs)

    if not match_pdf_pairs:
        console.print(
            f"  [yellow]Aucun PDF trouvé pour les {len(matches_db)} matchs. "
            f"Lancez d'abord : spyke import --only download[/yellow]"
        )
        return

    import os

    max_workers = min(8, os.cpu_count() or 4)

    console.print(
        f"  [magenta]●[/magenta] Matchs à parser : [bold]{len(match_pdf_pairs)}[/bold]  [dim]│[/dim]  "
        f"Moteur : [cyan]{parser.name} v{parser.version}[/cyan]  [dim]│[/dim]  "
        f"Fils : [cyan]{max_workers}[/cyan]"
    )
    if missing_pdf_count:
        console.print(f"  [dim]↷ {missing_pdf_count} match(s) ignoré(s) : PDF introuvable[/dim]")

    enriched = 0
    skipped_count = 0
    failed = 0
    warnings_count = 0
    plausibility_touched = 0
    plausibility_flagged = 0
    results = []
    error_details = []
    enriched_match_ids: list[int] = []

    with DatabaseSession() as session:
        orchestrator = IngestionOrchestrator(
            session=session,
            saison=getattr(matches_db[0], "saison_code", None) or "2024/2025",
        )
        service = orchestrator.match_details_stage

        import_log = ImportLogDB(
            operation="parse-enrich",
            source="import-pipeline",
            total_attempted=len(match_pdf_pairs),
            status="running",
        )
        session.add(import_log)
        session.flush()
        import_log_id = import_log.id

        with sqlite_bulk_mode(session), make_progress(console, refresh_per_second=8) as progress:
            task = progress.add_task(
                "[magenta]Parsing des feuilles de match...[/magenta]",
                total=len(match_pdf_pairs),
            )

            from concurrent.futures import ThreadPoolExecutor
            from queue import Queue
            from threading import Thread

            parse_queue: Queue = Queue(maxsize=150)
            _sentinel = object()

            def _parse_worker(pair):
                m_id, p_path = pair
                try:
                    res = parser.parse(p_path)
                    return m_id, p_path, res, None
                except Exception as exc:
                    return m_id, p_path, None, exc

            def _producer():
                try:
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        for item in executor.map(_parse_worker, match_pdf_pairs, chunksize=8):
                            parse_queue.put(item)
                finally:
                    parse_queue.put(_sentinel)

            producer_thread = Thread(target=_producer, daemon=True)
            producer_thread.start()

            batch_size = 200
            is_done = False

            while not is_done:
                batch_items = []
                while len(batch_items) < batch_size:
                    item = parse_queue.get()
                    if item is _sentinel:
                        is_done = True
                        break
                    batch_items.append(item)

                if not batch_items:
                    break

                chunk_ids = [it[0] for it in batch_items]
                chunk_matches = (
                    session.scalars(
                        select(MatchDB)
                        .options(
                            joinedload(MatchDB.saison),
                            joinedload(MatchDB.competition).joinedload(CompetitionDB.entite),
                            joinedload(MatchDB.poule),
                        )
                        .where(MatchDB.id.in_(chunk_ids))
                    )
                    .unique()
                    .all()
                )
                match_map = {m.id: m for m in chunk_matches}

                for match_id, pdf_path, result, parse_error in batch_items:
                    match_fresh = match_map.get(match_id)
                    if not match_fresh:
                        skipped_count += 1
                        progress.advance(task, 1)
                        continue

                    if parse_error:
                        failed += 1
                        match_fresh.parsing_status = "error"
                        match_fresh.remarques = str(parse_error)[:200]
                        error_details.append(
                            {
                                "file": str(pdf_path),
                                "errors": [str(parse_error)],
                            }
                        )
                        progress.advance(task, 1)
                        continue

                    try:
                        if result.success and result.match:
                            was_enriched = service.enrich_from_pdf(
                                match_fresh,
                                result.match,
                                force=force,
                                defer_rollups=True,
                                defer_player_stats=defer_player_stats,
                                import_log_id=import_log_id,
                            )
                            if was_enriched:
                                enriched += 1
                                enriched_match_ids.append(match_fresh.id)
                            else:
                                skipped_count += 1

                            results.append(
                                {
                                    "file": str(pdf_path),
                                    "parse_time_ms": result.parse_time_ms,
                                    "diagnostics": result.diagnostics,
                                    "plausibility_report": (
                                        result.plausibility_report.to_dict() if result.plausibility_report else None
                                    ),
                                    "enriched": was_enriched,
                                }
                            )

                            if result.diagnostics:
                                warnings_count += result.warnings_count
                            plausibility_touched += result.plausibility_changes_count
                            plausibility_flagged += result.plausibility_flagged_count

                            if verbose and was_enriched:
                                m = result.match
                                progress.console.print(
                                    f"  [green]✓[/green] {match_fresh.code_match}: "
                                    f"{m.equipe_a.nom[:20] if m.equipe_a else '?'} vs "
                                    f"{m.equipe_b.nom[:20] if m.equipe_b else '?'}"
                                )
                        else:
                            failed += 1
                            match_fresh.parsing_status = "error"
                            match_fresh.remarques = result.errors[0][:200] if result.errors else "Erreur de parsing"
                            error_details.append(
                                {
                                    "file": str(pdf_path),
                                    "errors": result.errors,
                                    "diagnostics": result.diagnostics,
                                }
                            )

                    except Exception as e:
                        failed += 1
                        match_fresh.parsing_status = "error"
                        match_fresh.remarques = str(e)[:200]
                        error_details.append(
                            {
                                "file": str(pdf_path),
                                "errors": [str(e)],
                            }
                        )

                    progress.advance(task, 1)

                # Commit par batch et purge de session en préservant les caches d'entités résolues
                try:
                    session.commit()
                    session.expunge_all()
                    service.clear_persistence_caches(clear_all=False)
                except Exception:
                    session.rollback()
                    service.clear_persistence_caches(clear_all=True)

            producer_thread.join()

        # Commit final
        import_log = session.get(ImportLogDB, import_log_id)
        if import_log:
            import_log.finished_at = datetime.now()
            import_log.imported = enriched
            import_log.duplicates = skipped_count
            import_log.errors = failed
            import_log.summary = json.dumps(
                {
                    "warnings": warnings_count,
                    "plausibility_touched": plausibility_touched,
                    "plausibility_flagged": plausibility_flagged,
                    "total_results": len(results),
                },
                ensure_ascii=False,
            )
            import_log.status = "success" if failed == 0 else "partial" if enriched > 0 else "failed"
        try:
            session.commit()
            session.expunge_all()
            service.clear_persistence_caches(clear_all=False)
        except Exception:
            session.rollback()
            service.clear_persistence_caches(clear_all=True)

        parse_work_duration = time.perf_counter() - t_parse_start

        # Calcul en lot des statistiques joueurs si différé
        if defer_player_stats and enriched_match_ids:
            t_stats_start = time.perf_counter()
            with make_progress(console, refresh_per_second=8) as stats_progress:
                stats_task = stats_progress.add_task(
                    "[cyan]Calcul des statistiques joueurs...",
                    total=len(enriched_match_ids),
                )
                total_player_rows = service.compute_player_stats(
                    enriched_match_ids,
                    chunk_size=50,
                    progress_callback=lambda n: stats_progress.advance(stats_task, n),
                )
                try:
                    session.commit()
                    session.expunge_all()
                    service.clear_persistence_caches(clear_all=False)
                except Exception:
                    session.rollback()
                    service.clear_persistence_caches(clear_all=True)

            stats_duration = time.perf_counter() - t_stats_start
            stats_rate = format_rate(len(enriched_match_ids), stats_duration, "matchs")
            console.print(
                f"  [cyan]✓ Statistiques joueurs calculées en {format_duration(stats_duration)} : "
                f"{len(enriched_match_ids)} matchs, {total_player_rows} lignes ({stats_rate})[/cyan]"
            )
            if timer:
                timer.record_sub_step(
                    "parse",
                    "player_stats",
                    "Calcul Stats Joueurs (différé)",
                    stats_duration,
                    items_count=len(enriched_match_ids),
                    items_unit="matchs",
                )

        # Actualisation consolidée des rollups si demandé
        if rollup and enriched_match_ids:
            from spyke.analysis.reporting.rollups import RollupStatsService

            t_rollups_start = time.perf_counter()
            with console.status(
                f"[bold magenta]Actualisation consolidée des rollups pour {len(enriched_match_ids)} match(s)...",
                spinner="dots",
            ):
                try:
                    rollup_service = RollupStatsService(session)
                    rollup_summary = rollup_service.apply_batch_deltas(enriched_match_ids)
                    session.commit()
                    rollups_duration = time.perf_counter() - t_rollups_start
                    total_rollups_items = (
                        rollup_summary.get("player_seasons_updated", 0)
                        + rollup_summary.get("teams_updated", 0)
                        + rollup_summary.get("clubs_updated", 0)
                        + rollup_summary.get("poules_updated", 0)
                    )
                    console.print(
                        f"  [magenta]✓ Rollups actualisés en {format_duration(rollups_duration)} : "
                        f"{rollup_summary.get('player_seasons_updated', 0)} stats joueurs, "
                        f"{rollup_summary.get('teams_updated', 0)} équipes, "
                        f"{rollup_summary.get('poules_updated', 0)} poules, "
                        f"{rollup_summary.get('clubs_updated', 0)} clubs ({format_rate(len(enriched_match_ids), rollups_duration, 'matchs')})[/magenta]"
                    )
                    if timer:
                        timer.record_sub_step(
                            "parse",
                            "rollups",
                            "Actualisation Rollups Consolidés",
                            rollups_duration,
                            items_count=total_rollups_items,
                            items_unit="agrégats",
                        )
                except Exception as exc:
                    console.print(f"  [yellow]⚠ Erreur lors de l'actualisation consolidée des rollups : {exc}[/yellow]")

    total_parse_duration = time.perf_counter() - t_parse_start
    if timer:
        timer.record_sub_step(
            "parse",
            "pdf_parse",
            "Parsing PDF & Injection Matchs",
            parse_work_duration,
            items_count=enriched,
            items_unit="matchs",
        )

    summary_grid = Table.grid(padding=(0, 3))
    summary_grid.add_column(style="bold cyan")
    summary_grid.add_column(style="white")
    summary_grid.add_column(style="bold cyan")
    summary_grid.add_column(style="white")

    summary_grid.add_row(
        "Matchs enrichis :",
        f"[bold green]✓ {enriched}[/bold green]",
        "Warnings PDF :",
        f"[yellow]⚠ {warnings_count}[/yellow]" if warnings_count else "[dim]0[/dim]",
    )
    summary_grid.add_row(
        "Inchangés :",
        f"[dim]= {skipped_count}[/dim]",
        "Plausibilité (modifs) :",
        f"[magenta]🧪 {plausibility_touched}[/magenta]" if plausibility_touched else "[dim]0[/dim]",
    )
    summary_grid.add_row(
        "Échecs :",
        f"[bold red]✗ {failed}[/bold red]" if failed else "[green]0[/green]",
        "Plausibilité (alertes) :",
        f"[magenta]🧪 {plausibility_flagged}[/magenta]" if plausibility_flagged else "[dim]0[/dim]",
    )
    summary_grid.add_row(
        "Durée totale :",
        f"[yellow]{format_duration(total_parse_duration)}[/yellow]",
        "Cadence moyenne :",
        f"[cyan]{format_rate(enriched, total_parse_duration, 'matchs')}[/cyan]",
    )

    console.print()
    console.print(
        Panel(
            summary_grid,
            title=f"[bold magenta]📊 Bilan du parsing & enrichissement[/bold magenta] [dim]({format_duration(total_parse_duration)})[/dim]",
            border_style="magenta",
            box=box.ROUNDED,
        )
    )

    if results or error_details:
        display_warning_summary(console, results, error_details, enriched + failed)
        display_plausibility_summary(console, results)


def _import_stream(
    *,
    limit: int | None = None,
    saison: list[str] | None = None,
    entity: list[str] | None = None,
    verbose: bool = False,
    concurrent: int = 10,
    plausibility: bool = True,
    plausibility_policy: str = "auto",
    review_fixes: bool = False,
    parser_name: str = "FastMatchSheetParser",
    rollup: bool = True,
    defer_player_stats: bool = True,
    timer: PipelineTimer | None = None,
) -> None:
    """Mode streaming : download → parse → DB, sans conserver les PDFs."""
    from concurrent.futures import ThreadPoolExecutor

    import httpx
    from spyke.infrastructure.database.connection import DatabaseSession, init_db, sqlite_bulk_mode
    from spyke.infrastructure.database.tables import ImportLogDB, MatchDB
    from spyke.ingestion import IngestionOrchestrator
    from spyke.parsers.fdme.factory import ParserFactory
    from sqlalchemy import or_, select

    init_db()
    today = dt_date.today()
    t_stream_start = time.perf_counter()
    parser = ParserFactory.get(parser_name)
    approval_cb = None
    if review_fixes:
        approval_cb = build_plausibility_reviewer(console)
    _configure_parser_plausibility(
        parser,
        enabled=plausibility,
        policy=plausibility_policy,
        approval=approval_cb,
    )

    with DatabaseSession() as session:
        stmt = select(MatchDB).where(
            MatchDB.parsing_status == "discovered",
            MatchDB.match_joue == True,  # noqa: E712
            MatchDB.source_url.isnot(None),
            or_(
                MatchDB.date_match.is_(None),
                MatchDB.date_match <= today,
            ),
        )
        stmt, _ = add_saison_filter(session, stmt, saison)
        stmt = add_entity_filter(session, stmt, entity)
        stmt = stmt.order_by(MatchDB.code_match)
        if limit:
            stmt = stmt.limit(limit)
        matches = list(session.scalars(stmt).all())

    if not matches:
        console.print("  [yellow]Aucun match à traiter[/yellow]")
        return

    max_workers = max(1, min(concurrent, 20))
    console.print(
        f"  [blue]⚡[/blue] Matchs ciblés en streaming : [bold]{len(matches)}[/bold]  [dim]│[/dim]  "
        f"Moteur : [cyan]{parser.name} v{parser.version}[/cyan]  [dim]│[/dim]  "
        f"Workers : [cyan]{max_workers}[/cyan]"
    )

    downloaded = 0
    enriched = 0
    failed = 0
    enriched_match_ids: list[int] = []

    limits = httpx.Limits(max_connections=max_workers + 5, max_keepalive_connections=max_workers)
    with httpx.Client(timeout=30, follow_redirects=True, limits=limits) as http, DatabaseSession() as session:
        with sqlite_bulk_mode(session):
            orchestrator = IngestionOrchestrator(session=session, saison="2024/2025")
            service = orchestrator.match_details_stage

            import_log = ImportLogDB(
                operation="stream-pipeline",
                source="streaming",
                total_attempted=len(matches),
                status="running",
            )
            session.add(import_log)
            session.flush()
            import_log_id = import_log.id

            targets = [(m.id, m.code_match, m.source_url) for m in matches if m.source_url]
            skipped_no_url = len(matches) - len(targets)

            def _fetch_and_parse(item):
                m_id, code_match, url = item
                try:
                    resp = http.get(url)
                    resp.raise_for_status()
                    if not resp.content[:5].startswith(b"%PDF"):
                        return m_id, code_match, None, "Réponse non-PDF"
                    parsed = parser.parse(resp.content)
                    return m_id, code_match, parsed, None
                except Exception as exc:
                    return m_id, code_match, None, str(exc)

            with make_progress(console, refresh_per_second=8) as progress:
                task = progress.add_task(
                    "[cyan]Streaming (Téléchargement + Analyse)...[/cyan]",
                    total=len(matches),
                )
                if skipped_no_url:
                    progress.advance(task, skipped_no_url)

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    for m_id, code_match, result, err_msg in executor.map(_fetch_and_parse, targets):
                        match_fresh = session.get(MatchDB, m_id)
                        if not match_fresh:
                            progress.advance(task, 1)
                            continue

                        if err_msg:
                            failed += 1
                            match_fresh.parsing_status = "error"
                            match_fresh.remarques = err_msg[:200]
                        elif result and result.success and result.match:
                            downloaded += 1
                            was_enriched = service.enrich_from_pdf(
                                match_fresh,
                                result.match,
                                force=True,
                                defer_rollups=True,
                                defer_player_stats=defer_player_stats,
                                import_log_id=import_log_id,
                            )
                            if was_enriched:
                                enriched += 1
                                enriched_match_ids.append(match_fresh.id)

                            if verbose:
                                m = result.match
                                progress.console.print(
                                    f"  [green]✓[/green] {match_fresh.code_match}: "
                                    f"{m.equipe_a.nom[:20] if m.equipe_a else '?'} vs "
                                    f"{m.equipe_b.nom[:20] if m.equipe_b else '?'}"
                                )
                        else:
                            downloaded += 1
                            failed += 1
                            match_fresh.parsing_status = "error"
                            match_fresh.remarques = (
                                result.errors[0][:200] if result and result.errors else "Erreur de parsing"
                            )

                        progress.advance(task, 1)

                        # Commit par batch et purge de session
                        if (enriched + failed) % 50 == 0 and (enriched + failed) > 0:
                            try:
                                session.commit()
                                session.expunge_all()
                                service.clear_persistence_caches(clear_all=False)
                            except Exception:
                                session.rollback()
                                service.clear_persistence_caches(clear_all=True)

            stream_work_duration = time.perf_counter() - t_stream_start

            import_log = session.get(ImportLogDB, import_log_id)
            if import_log:
                import_log.finished_at = datetime.now()
                import_log.imported = enriched
                import_log.errors = failed
                import_log.status = "success" if failed == 0 else "partial" if enriched > 0 else "failed"
            try:
                session.commit()
                session.expunge_all()
                service.clear_persistence_caches(clear_all=False)
            except Exception:
                session.rollback()
                service.clear_persistence_caches(clear_all=True)

            # Calcul en lot des statistiques joueurs si différé
            if defer_player_stats and enriched_match_ids:
                t_stats_start = time.perf_counter()
                with make_progress(console, refresh_per_second=8) as stats_progress:
                    stats_task = stats_progress.add_task(
                        "[cyan]Calcul des statistiques joueurs (streaming)...",
                        total=len(enriched_match_ids),
                    )
                    service.compute_player_stats(
                        enriched_match_ids,
                        chunk_size=50,
                        progress_callback=lambda n: stats_progress.advance(stats_task, n),
                    )
                    try:
                        session.commit()
                        session.expunge_all()
                        service.clear_persistence_caches(clear_all=False)
                    except Exception:
                        session.rollback()
                        service.clear_persistence_caches(clear_all=True)

                stats_duration = time.perf_counter() - t_stats_start
                console.print(
                    f"  [cyan]✓ Statistiques joueurs calculées en {format_duration(stats_duration)} "
                    f"({format_rate(len(enriched_match_ids), stats_duration, 'matchs')})[/cyan]"
                )
                if timer:
                    timer.record_sub_step(
                        "stream",
                        "player_stats",
                        "Calcul Stats Joueurs (différé)",
                        stats_duration,
                        items_count=len(enriched_match_ids),
                        items_unit="matchs",
                    )

        # Actualisation consolidée des rollups si demandé
        if rollup and enriched_match_ids:
            from spyke.analysis.reporting.rollups import RollupStatsService

            t_rollups_start = time.perf_counter()
            with console.status(
                f"[bold magenta]Actualisation consolidée des rollups pour {len(enriched_match_ids)} match(s)...",
                spinner="dots",
            ):
                try:
                    rollup_service = RollupStatsService(session)
                    rollup_summary = rollup_service.apply_batch_deltas(enriched_match_ids)
                    session.commit()
                    rollups_duration = time.perf_counter() - t_rollups_start
                    console.print(
                        f"  [magenta]✓ Rollups actualisés en {format_duration(rollups_duration)} "
                        f"({format_rate(len(enriched_match_ids), rollups_duration, 'matchs')})[/magenta]"
                    )
                    if timer:
                        timer.record_sub_step(
                            "stream",
                            "rollups",
                            "Actualisation Rollups Consolidés",
                            rollups_duration,
                            items_count=len(enriched_match_ids),
                            items_unit="matchs",
                        )
                except Exception as exc:
                    console.print(f"  [yellow]⚠ Erreur rollups streaming : {exc}[/yellow]")

    total_stream_duration = time.perf_counter() - t_stream_start
    stream_rate = format_rate(enriched, total_stream_duration, "matchs")
    if timer:
        timer.record_sub_step(
            "stream",
            "stream_dl_parse",
            "Streaming Download & Parse",
            stream_work_duration,
            items_count=enriched,
            items_unit="matchs",
        )

    console.print(
        f"\n[green]✓ {enriched} enrichis en {format_duration(total_stream_duration)} ({stream_rate})[/green]"
        + (f" [dim]│[/dim] [red]{failed} erreurs[/red]" if failed else "")
    )
