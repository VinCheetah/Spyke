from dataclasses import dataclass


@dataclass(frozen=True)
class FfvbEndpoints:
    """Relative endpoints used by the first FFVolley referential importer."""

    leagues: str = "/leagues"
    clubs: str = "/clubs"
    competitions: str = "/competitions"
    calendar: str = "/calendar"
