from dataclasses import dataclass


@dataclass(frozen=True)
class FfvbEndpoints:
    """
    Relative endpoints used by the FFVolley adapters.
    """

    entities: str = "/planning_volley.php"
    clubs: str = "/adressier/rech_aff_club.php"
    clubs_adressier: str = "/adressier/adressier_pdf.php"
    competitions: str = "/competitions"
    calendar: str = "/calendar"
    calendar_export: str = "/vbspo_calendrier_export.php"
    match_sheet: str = "/ffvolley_fdme.php"
