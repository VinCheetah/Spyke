

from abc import ABC, abstractmethod
import re
from typing import Any, Generic, TypeVar

from spyke.infrastructure.ffvb.dto import Record
from spyke.infrastructure.sources.http import HttpDocument
from bs4 import BeautifulSoup, Tag


T_RecordType = TypeVar("T_RecordType", bound=Record)

class BaseParser(ABC, Generic[T_RecordType]):
    """Base class for all parsers."""

    @abstractmethod
    def parse(self, document: Any) -> list[T_RecordType]:
        """Parse a document and return a list of records.

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

    @abstractmethod
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
        return BeautifulSoup(document.body, "lxml")

    def find_heading(self, soup: BeautifulSoup, title: str) -> Tag:
        """Find a unique section heading cell by its visible text."""
        matches = [td for td in soup.find_all("td") if self.clean_text(td) == title]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one heading {title!r}, found {len(matches)}"
            )
        return matches[0]