import re
import unicodedata

from spyke.domain.enums import Category

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
