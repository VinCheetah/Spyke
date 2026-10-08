from datetime import datetime
from typing import Any, cast

from spyke.domain.enums import Category, Division, Echelon, Gender, MatchStatus
from spyke.infrastructure.ffvb.dto import (
    ClubRecord,
    CompetitionRecord,
    EntityRecord,
    MatchRecord,
)


class JsonReferentialParser:
    """Parse the stable, source-neutral JSON contract used by referential imports.

    The adapter deliberately accepts either a top-level list or an object whose
    collection is under the expected key. Source-specific field mapping remains
    here, keeping the application import service independent from FFVolley JSON.
    """

    def leagues(self, payload: Any) -> list[EntityRecord]:
        return [
            EntityRecord(
                name=self._text(item, "name"),
                code_ffvb=self._text(item, "code_ffvb", "code"),
            )
            for item in self._items(payload, "leagues")
        ]

    def clubs(self, payload: Any) -> list[ClubRecord]:
        return [
            ClubRecord(
                external_id=self._text(item, "id"),
                name=self._text(item, "name"),
                code_ffvb=int(self._text(item, "code_ffvb", "code")),
                city=self._optional_text(item, "city"),
                department=self._optional_text(item, "department"),
                league_external_id=self._optional_text(item, "league_id"),
            )
            for item in self._items(payload, "clubs")
        ]

    def competitions(self, payload: Any) -> list[CompetitionRecord]:
        return [
            CompetitionRecord(
                external_id=self._text(item, "id"),
                name=self._text(item, "name"),
                code=self._text(item, "code"),
                season_start=int(self._text(item, "season_start")),
                season_end=int(self._text(item, "season_end")),
                organizer_external_id=self._text(item, "organizer_id"),
                gender=Gender[self._text(item, "gender")],
                category=Category[self._text(item, "category")],
                echelon=Echelon[self._text(item, "echelon")],
                division=Division[self._text(item, "division")],
            )
            for item in self._items(payload, "competitions")
        ]

    def calendar(self, payload: Any) -> list[MatchRecord]:
        return [
            MatchRecord(
                external_id=self._text(item, "id"),
                code=self._text(item, "code"),
                competition_external_id=self._text(item, "competition_id"),
                home_club_external_id=self._text(item, "home_club_id"),
                away_club_external_id=self._text(item, "away_club_id"),
                scheduled_at=self._datetime(item, "scheduled_at"),
                status=MatchStatus[self._text(item, "status")],
            )
            for item in self._items(payload, "matches")
        ]

    @staticmethod
    def _items(payload: Any, key: str) -> list[dict[str, Any]]:
        items: list[Any]
        if isinstance(payload, list):
            items = cast(list[Any], payload)
        elif isinstance(payload, dict):
            payload_dict = cast(dict[str, Any], payload)
            if not isinstance(payload_dict.get(key), list):
                raise ValueError(f"Expected a list or an object containing '{key}'")
            items = cast(list[Any], payload_dict[key])
        else:
            raise ValueError(f"Expected a list or an object containing '{key}'")
        if not all(isinstance(item, dict) for item in items):
            raise ValueError(f"Every item in '{key}' must be an object")
        return cast(list[dict[str, Any]], items)

    @staticmethod
    def _text(item: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = item.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        raise ValueError(f"Missing required field: {' or '.join(keys)}")

    @classmethod
    def _optional_text(cls, item: dict[str, Any], key: str) -> str | None:
        value = item.get(key)
        return str(value).strip() if value is not None and str(value).strip() else None

    @classmethod
    def _datetime(cls, item: dict[str, Any], key: str) -> datetime:
        value = cls._text(item, key).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"Invalid datetime in field '{key}': {value}") from error
