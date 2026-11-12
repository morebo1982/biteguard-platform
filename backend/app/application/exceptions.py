"""Application-layer exceptions with stable, transport-neutral semantics."""


class ApplicationError(Exception):
    """Base class for expected application failures."""


class EntityNotFoundError(ApplicationError):
    """Raised when a requested entity does not exist."""


class EntityConflictError(ApplicationError):
    """Raised when an entity conflicts with an existing business key."""


class InvalidOperationError(ApplicationError):
    """Raised when an operation violates an application business rule."""
