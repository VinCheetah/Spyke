import re
from abc import ABC
from pathlib import Path
from typing import Any, Generic, TypeVar

from bs4 import BeautifulSoup, Tag

from spyke.infrastructure.ffvb.dto import Record
from spyke.infrastructure.sources.http import HttpDocument

T_RecordType = TypeVar("T_RecordType", bound=Record)


class BaseParser(Generic[T_RecordType], ABC):
    def clean(self, record: T_RecordType) -> T_RecordType:
        """Clean a record by normalizing its string attributes."""
        pass

    def parse(self, document: Any) -> list[T_RecordType]:
        """Parse a document and return a list of records.

        Args:
            document (HttpDocument): The document to parse.
        """
        pass

    def parse_record(self, document: Any) -> T_RecordType:
        """Parse a document and return a single record.

        Args:
            document (HttpDocument): The document to parse.
        """
        pass

    def enrich(self, records: list[T_RecordType], document: Any) -> None:
        """Enrich a record with additional details from a document.

        Args:
            record (Record): The record to enrich.
            document (HttpDocument): The document containing additional details.

        Returns:
            list[Record]: The enriched records.
        """
        pass

    @staticmethod
    def _clean_str(val: str | None) -> str | None:
        """Clean a string by stripping whitespace and returning None if empty.

        Args:
            val (str | None): The string to clean.

        Returns:
            str | None: The cleaned string, or None if it's empty.
        """
        if val is None:
            return None
        cleaned = val.strip()
        return cleaned if cleaned else None

    @staticmethod
    def clean_text(element: Tag | None) -> str | None:
        """Return normalized text, or None when empty."""
        if element is None:
            return None

        text = re.sub(r"\s+", " ", element.get_text(" ", strip=True))
        return text or None


class HttpDocumentParser(BaseParser[T_RecordType]):
    T_RecordType = TypeVar("T_RecordType", bound=Record)

    def parse(self, document: HttpDocument) -> list[T_RecordType]:
        """Parse a document and return a list of records.

        Args:
            document (HttpDocument): The document to parse.
        """

    def enrich(self, records: list[T_RecordType], document: HttpDocument) -> None:
        """Enrich a record with additional details from a document.

        Args:
            record (Record): The record to enrich.
            document (HttpDocument): The document containing additional details.

        Returns:
            list[Record]: The enriched records.
        """
        raise NotImplementedError("Subclasses must implement the enrich method.")

    def enrich_record(self, record: T_RecordType, document: HttpDocument) -> None:
        """Enrich a record with additional details from a document.

        Args:
            record (Record): The record to enrich.
            document (HttpDocument): The document containing additional details.
        Returns:
            Record: The enriched record.
        """
        raise NotImplementedError("Subclasses must implement the enrich_record method.")

    @staticmethod
    def get_soup(document: HttpDocument) -> Any:
        """Convert an HTTP document to a BeautifulSoup object.

        Args:
            document (HttpDocument): The HTTP document to convert.

        Returns:
            BeautifulSoup: A BeautifulSoup object representing the parsed HTML.
        """
        soup = BeautifulSoup(document.body, "lxml")
        path = Path("/tmp/soup.html")
        path.write_text(soup.prettify())
        return BeautifulSoup(document.body, "lxml")

    def find_heading(self, soup: BeautifulSoup | Tag, title: str) -> Tag:
        """Find a unique section heading cell by its visible text."""
        matches = [td for td in soup.find_all("td") if self.clean_text(td) == title]
        if len(matches) != 1:
            raise ValueError(f"Expected one heading {title!r}, found {len(matches)}")
        return matches[0]

    @staticmethod
    def _email(node: Tag) -> str | None:
        link = node.find("a", href=re.compile(r"^mailto:", re.I))
        if link is None:
            return None
        href = link.get("href")
        return href[7:].strip() if isinstance(href, str) else None

    @staticmethod
    def _website(node: Tag) -> str | None:
        # Le lien peut etre https ou http ou // s'adapter à tout les cas est important
        link = node.find("a", href=re.compile(r"^(https?://|//)", re.I))
        if link is None:
            return None
        href = link.get("href")
        return href.strip() if isinstance(href, str) else None

    def get_grandparent(self, tag: Tag | None) -> Tag | None:
        """Get the grandparent of a BeautifulSoup tag."""
        if tag is None:
            return None
        if (parent := tag.parent) is None:
            return None
        if (grandparent := parent.parent) is None:
            return None
        return grandparent
