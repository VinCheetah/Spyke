from datetime import date

import pytest

from spyke.domain.entities.match import Formation, MatchScore, SetScore
from spyke.domain.entities.organisation import Season
from spyke.domain.enums import Category, Side
from spyke.domain.rules.categorisation import is_youth_category, normalize_text_upper
from spyke.domain.types import CodeClub, Jersey, SetNumber


def test_season_round_trips_through_its_code() -> None:
    season = Season.from_code("2025-2026")

    assert season.start_date == date(2025, 9, 1)
    assert season.end_date == date(2026, 8, 31)
    assert season.code == "2025-2026"


@pytest.mark.parametrize("code", ["2025", "2025/2026", "2025-2027", "abc-def"])
def test_season_rejects_invalid_code(code: str) -> None:
    with pytest.raises(ValueError, match="Code de saison invalide"):
        Season.from_code(code)


def test_domain_value_objects_reject_invalid_values() -> None:
    with pytest.raises(ValueError):
        Jersey(100)
    with pytest.raises(ValueError):
        CodeClub(999_999)
    with pytest.raises(ValueError):
        SetNumber(6)


def test_match_score_calculates_set_winner_and_match_winner() -> None:
    score = MatchScore(sets_score=[SetScore(25, 20), SetScore(21, 25), SetScore(25, 22)])

    assert str(score) == "25-20/21-25/25-22"
    assert score.sets_score_str() == "2/1"
    assert score.winner == Side.A


def test_empty_formation_can_be_serialized_by_position() -> None:
    formation = Formation()

    assert formation.as_list() == [None] * 6
    assert list(formation.as_dict()) == ["I", "II", "III", "IV", "V", "VI"]


def test_category_and_text_rules_normalize_external_values() -> None:
    assert is_youth_category(Category.M18)
    assert not is_youth_category(Category.SENIOR)
    assert normalize_text_upper("  Équipe\t féminine  ") == "EQUIPE FEMININE"
