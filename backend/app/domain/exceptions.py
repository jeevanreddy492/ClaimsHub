"""Business exceptions. The API layer maps each one to an HTTP status code."""


class DomainError(Exception):
    """Base class. `code` is a stable, machine-readable error code."""

    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationError(DomainError):
    status_code = 422
    code = "VALIDATION_FAILED"


class ConflictError(DomainError):
    status_code = 409
    code = "CONFLICT"


class InvalidStatusTransitionError(ConflictError):
    code = "INVALID_STATUS_TRANSITION"


class VersionConflictError(ConflictError):
    code = "VERSION_CONFLICT"


class AuthError(DomainError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(DomainError):
    status_code = 403
    code = "FORBIDDEN"


# Custom error numbers raised by CLAIMS_PKG (RAISE_APPLICATION_ERROR).
ORACLE_ERROR_MAP: dict[int, type[DomainError]] = {
    20001: InvalidStatusTransitionError,
    20002: VersionConflictError,
    20003: NotFoundError,
    20004: ValidationError,  # beneficiary shares do not add up to 100
    20005: ValidationError,  # benefit calculation not possible
}
