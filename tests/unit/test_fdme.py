from typing import Any

import pymupdf
import pytest

from spyke.infrastructure.fdme.ffvb import FfvbFdmeParseError, FfvbPdfParser, FfvbTextParser
from spyke.infrastructure.fdme.models import ParsedSet
from spyke.infrastructure.fdme.registry import FdmeRegistry, UnknownFdmeFormat

FFVB_TEXT = """FFVB FDME
MATCH: M-2026-001
EQUIPE A: AS Lyon
EQUIPE B: Volley Lille
JOUEUR A: 4 DUPONT Jean*
JOUEUR A: 7 MARTIN Lea[L]
JOUEUR B: 9 DURAND Paul
ENTRAINEUR A: COACH Alice
ARBITRE 1: REFEREE Bob
SETS: 25-20, 25-22, 22-25, 25-18
"""


def test_ffvb_parser_extracts_only_available_robust_facts() -> None:
    parsed = FfvbTextParser().parse(FFVB_TEXT)

    assert parsed.match.code == "M-2026-001"
    assert parsed.match.team_a.name == "AS Lyon"
    assert parsed.match.team_a.players[0].captain
    assert parsed.match.team_a.players[1].libero
    assert parsed.match.score == (3, 1)
    assert parsed.match.sets == (
        ParsedSet(1, 25, 20),
        ParsedSet(2, 25, 22),
        ParsedSet(3, 22, 25),
        ParsedSet(4, 25, 18),
    )
    assert "rotations" not in parsed.capabilities


def test_registry_rejects_unknown_format() -> None:
    registry = FdmeRegistry([FfvbTextParser()])

    with pytest.raises(UnknownFdmeFormat):
        registry.parse("unrelated document")


def test_ffvb_parser_rejects_missing_set_scores() -> None:
    text = FFVB_TEXT.replace("SETS: 25-20, 25-22, 22-25, 25-18", "SETS: unavailable")

    with pytest.raises(FfvbFdmeParseError, match="No valid set score"):
        FfvbTextParser().parse(text)


def test_ffvb_pdf_adapter_delegates_extracted_text_to_parser() -> None:
    document: Any = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), FFVB_TEXT)
    content = document.tobytes()
    document.close()

    parsed = FfvbPdfParser().parse(content)

    assert parsed.match.code == "M-2026-001"
    assert parsed.match.score == (3, 1)
