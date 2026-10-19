from typing import Annotated

import typer

from spyke.domain.enums import ArchiveMode

SeasonParam = Annotated[
    list[str],
    typer.Option(
        "--saison",
        "-s",
        help="Saisons à importer (ex: 23/24 ou 21/25).",
        metavar="Saison",
    ),
]

EntityParam = Annotated[
    list[str],
    typer.Option(
        "--entite",
        "-e",
        help="Code des Entités à traiter (ex: LIRA, PTRA69, ABCCS, ...).",
        metavar="Entité FFVB",
    ),
]


LimitParam = Annotated[
    int | None,
    typer.Option(
        "--limit",
        "-l",
        help="Nombre maximum d'éléments à traiter (ex: 10).",
    ),
]

ForceParam = Annotated[
    bool,
    typer.Option(
        "--force",
        "-f",
        help="Re-traiter les éléments déjà parsés.",
        is_flag=True,
    ),
]

DryRunParam = Annotated[
    bool,
    typer.Option(
        "--dry-run",
        "-d",
        help="Exécuter le traitement sans enregistrer les modifications.",
        is_flag=True,
    ),
]

VerboseParam = Annotated[
    bool,
    typer.Option(
        "--verbose",
        "-v",
        help="Afficher les détails du traitement.",
        is_flag=True,
    ),
]


ArchiveModeParam = Annotated[
    ArchiveMode,
    typer.Option(
        "--archive",
        "-a",
        help="Mode d'utilisation de l'archive (DISABLED, USE, REFRESH, OFFLINE).",
        case_sensitive=False,
        metavar="ARCHIVE",
    ),
]

AllEntitiesParam = Annotated[
    bool,
    typer.Option(
        "--all-entities",
        "-all",
        help="Importer toutes les entités disponibles.",
        is_flag=True,
    ),
]
