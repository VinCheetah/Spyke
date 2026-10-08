def format_entities_display(entities: list[str], max_show: int = 5) -> str:
    """Formate une liste d'entités pour l'affichage."""
    display = ", ".join(entities[:max_show])
    if len(entities) > max_show:
        display += f"... (+{len(entities) - max_show})"
    return display


def max_show(strings: list[str], max_show: int = 5, sep: str = ", ") -> str:
    """Tronque les chaînes de caractères pour ne pas dépasser une longueur maximale."""
    display = ", ".join(strings[:max_show])
    if len(strings) > max_show:
        display += f"... (+{len(strings) - max_show})"
    return display
