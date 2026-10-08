from dataclasses import dataclass
from typing import Generic, TypeVar

from spyke.infrastructure.database.base import Base
from spyke.infrastructure.ffvb.dto import Record
from abc import abstractmethod, ABC
from spyke.infrastructure.database.session import Session


@dataclass(frozen=True)
class ImportSummary:
    """Counters returned by one idempotent referential import."""

    seen: int
    created: int
    updated: int


T_RecordType = TypeVar("T_RecordType", bound=Record)
T_ModelType = TypeVar("T_ModelType", bound=Base)


# La classe abstraite devient générique
class BaseImporter(ABC, Generic[T_RecordType, T_ModelType]):
    """Base class for all importers."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # How should i manage to have different type of Record (subtypes) in the import_records method ?

    @abstractmethod
    def import_records(self, records: list[T_RecordType]) -> ImportSummary:
        """Import a list of records into the database.

        Args:
            records (list[Record]): The list of records to import.

        Returns:
            ImportSummary: A summary of the import operation.
        """
        raise NotImplementedError("Subclasses must implement the import_records method.")

    @abstractmethod
    def find_or_create(self, record: T_RecordType) -> tuple[T_ModelType, bool]:
        """Find an existing record in the database or create a new one.

        Args:
            record (Record): The record to find or create.

        Returns:
            tuple[BaseModel, bool]: A tuple containing the model instance and a boolean indicating whether it was created.
        """
        raise NotImplementedError("Subclasses must implement the find_or_create method.")
