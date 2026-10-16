"""
Interface CLI principale pour PyVolley.

Point d'entrée modulaire orchestrant les commandes principales et les sous-applications :
- ``import``        : importer des données FFVB (scrape → download → parse)
- ``status``        : tableau de bord du pipeline d'import
- ``parse``         : analyser un PDF de feuille de match
- ``serve``         : lancer le serveur web
- ``simulate``      : visualiser un match en HTML interactif
- ``cleanup``       : nettoyer les PDFs locaux

Sous-applications :
- ``compute``       : calculs statistiques (all, players, rollups, palmares)
- ``audit``         : audits de qualité (vraisemblance, rôles, niveaux de compétition)
- ``db``            : gestion, initialisation et migrations de la base de données
- ``dev``           : outils développeur (benchmarks parsers, layout-editor)
- ``list``          : consultation FFVB en direct (entités, poules, matchs)
- ``roles``         : inférence et diffusion réseau des rôles joueurs
- ``sync``          : synchronisation des données externes (logos, géocodage)
"""

from __future__ import annotations

import logging
import sys
import typer
from time import strftime
from pathlib import Path
from rich.console import Console

from spyke.cli.logging_config import configure_logging
from spyke.config import settings

# Configuration console Windows UTF-8
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Application Typer racine
app = typer.Typer(
    name="spyke",
    help="Spyke — Outils pour les données volleyball FFVB",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


from spyke.cli.commands.import_cmd import import_data
from spyke.cli.commands.debug_cmd import debug

configure_logging(
        level=logging.INFO,
        log_file=settings.base_dir / f"logs/spyke_{strftime('%Y%m%d_%H%M%S')}.log",
    )
# ── Commandes racines principales ──────────────────────────────────────────
app.command("import")(import_data)
app.command("debug")(debug)
app.command("prout")(lambda: console.print("[bold red]Prout![/bold red]"))


def main():
    """Point d'entrée principal du CLI."""

    configure_logging(
        level=logging.DEBUG,
        log_file=settings.base_dir / f"logs/spyke_{strftime('%Y%m%d_%H%M%S')}.log",
    )

    logger = logging.getLogger(__name__)
    logger.info("Spyke starting")
    app()


if __name__ == "__main__":
    main()
