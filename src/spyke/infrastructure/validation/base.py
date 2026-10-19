from typing import Generic

from spyke.domain.types import T_RecordType


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


class ValidationResult:
    """Class to hold the result of a validation."""

    def __init__(self, is_valid: bool, errors: list[str] | None = None):
        self.is_valid = is_valid
        self.errors = errors or []


class BaseValidator(Generic[T_RecordType]):
    """Base class for validators."""

    def validate(self, record: T_RecordType) -> ValidationResult:
        """Validate a record.

        Args:
            record (T_RecordType): The record to validate.

        Returns:
            ValidationResult: The result of the validation.
        """
        raise NotImplementedError("Subclasses must implement the validate method.")
