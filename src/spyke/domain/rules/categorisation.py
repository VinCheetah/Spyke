import re
import unicodedata

from spyke.domain.enums import Category, Echelon

_RE_SPACES = re.compile(r"\s+")


def is_youth_category(category: Category) -> bool:
    """_summary_

    Args:
        category (Category): _description_

    Returns:
        bool: _description_
    """
    return category in {
        Category.M11,
        Category.M13,
        Category.M15,
        Category.M18,
        Category.M21,
        Category.JEUNES,
    }


def normalize_text_upper(value: str) -> str:
    """Supprime les accents, normalise les espaces et met en majuscules."""
    if not value:
        return ""
    norm = unicodedata.normalize("NFD", value)
    without_accents = "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")
    return _RE_SPACES.sub(" ", without_accents).strip().upper()


def get_echelon_from_code_ffvb(code_ffvb: str) -> Echelon:
    """Extract the echelon from the FFVB code.

    Args:
        code_ffvb (str): The FFVB code.

    Returns:
        Echelon: The corresponding Echelon enum value.
    """
    if code_ffvb.startswith("A"):
        return Echelon.NATIONAL
    elif code_ffvb.startswith("LI"):
        return Echelon.REGIONAL
    elif code_ffvb.startswith("PT"):
        return Echelon.DEPARTEMENTAL
    else:
        raise ValueError(f"Code d'entité FFVB inconnu: {code_ffvb}")
