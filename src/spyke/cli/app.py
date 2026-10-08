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

import sys
import typer
from rich.console import Console

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


# ── Commandes racines principales ──────────────────────────────────────────
app.command("import")(import_data)


def main():
    """Point d'entrée principal du CLI."""
    app()


if __name__ == "__main__":
    main()
