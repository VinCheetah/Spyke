from dataclasses import dataclass, field


@dataclass(frozen=True)
class FfvbEndpoints:
    """
    Relative endpoints used by the FFVolley adapters.
    """

    entities: str = "/resu/planning_volley.php"
    entities_directory: str = "/adressier/recherche.php"
    clubs: str = "/adressier/rech_aff_club.php"
    clubs_adressier: str = "/adressier/adressier_pdf.php"
    competitions: str = "/resu/vbspo_home.php"
    calendar: str = "/calendar"
    calendar_export: str = "/resu/vbspo_calendrier_export.php"
    match_sheet: str = "/ffvolley_fdme.php"

    entities_directory_params: dict[str, str] = field(
        default_factory=lambda: {
            "ws_new_ligue": "0",
            "ws_new_comit": "0",
            "ws_list_dep": "",
            "id_club": "",
        }
    )
