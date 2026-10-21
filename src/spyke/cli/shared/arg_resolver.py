from spyke.domain.entities import Season
from spyke.domain.enums import Echelon


def resolve_seasons(seasons: list[str]) -> list[Season]:
    """
    Resolve a list of season codes into Season objects.

    Args:
        seasons (list[str]): List of season codes (e.g., ["2022/2023", "2021/2024", "23/25]).

    Returns:
        list[Season]: List of Season objects corresponding to the provided codes.
    """
    resolved: list[Season] = []
    for season in seasons:
        split_season = season.split("/")
        assert len(split_season) == 2, f"Saison invalide: {season}"
        start_year, end_year = split_season
        if len(start_year) == 2:
            start_year = f"20{start_year}"
        if len(end_year) == 2:
            end_year = f"20{end_year}"
        assert len(start_year) == len(end_year) == 4, f"Saison invalide: {season}"
        assert start_year.isdigit() and end_year.isdigit(), f"Saison invalide: {season}"
        assert int(start_year) <= int(end_year), f"Saison invalide: {season}"
        resolved.extend(
            list(Season.from_code(f"{start}") for start in range(int(start_year), int(end_year)))
        )
    return resolved


def resolve_entity_type(entity_type: str) -> Echelon:
    """
    Resolve the entity type string into a valid entity type.

    Args:
        entity_type (str): The entity type string to resolve. Possible values are "NATIONAL", "REGIONAL", or "DEPARTMENTAL".

    Returns:
        Echelon: The corresponding Echelon enum value.
    """
    formatted_type = entity_type.strip().upper()
    if formatted_type not in Echelon.__members__:
        raise ValueError(f"Type d'entité invalide: {entity_type}")
    return Echelon[formatted_type]
