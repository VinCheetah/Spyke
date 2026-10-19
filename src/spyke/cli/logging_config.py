import logging
from pathlib import Path


def configure_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
) -> None:
    root = logging.getLogger()

    # --- AJOUTEZ CECI POUR NETTOYER LES ANCIENS HANDLERS ---
    if root.hasHandlers():
        root.handlers.clear()
    # --------------------------------------------------------

    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(
            log_file,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
