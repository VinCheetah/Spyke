from spyke.infrastructure.ffvb.dto import EntityRecord


class EntityValidator:
    """Validator for EntityRecord."""

    def validate(self, record: EntityRecord) -> None:
        """Validate the given EntityRecord."""
        if not record.code_ffvb:
            raise ValueError("Entity code_ffvb is required.")
        if not record.name:
            raise ValueError("Entity name is required.")
        if not record.entity_type:
            raise ValueError("Entity type is required.")
