"""Domain error taxonomy.

Third-party / SDK exceptions NEVER cross a provider boundary. Each integration
maps its own failures into exactly one of these types (docs/INTEGRATION-ARCHITECTURE.md §9).
"""

from __future__ import annotations

from typing import ClassVar


class DomainError(Exception):
    """Base class for all domain & application errors.

    `retryable` drives upstream retry policy; `provider` tags the failing
    integration for observability without leaking vendor types.
    """

    error_code: ClassVar[str] = "domain_error"
    retryable: ClassVar[bool] = False

    def __init__(self, message: str, *, provider: str | None = None, cause: Exception | None = None) -> None:
        self.message = message
        self.provider = provider
        self.cause = cause
        super().__init__(message)


class ProviderUnavailableError(DomainError):
    error_code = "provider_unavailable"
    retryable = True


class RateLimitedError(DomainError):
    error_code = "rate_limited"
    retryable = True


class ProviderTimeoutError(DomainError):
    error_code = "provider_timeout"
    retryable = True


class AuthenticationError(DomainError):
    error_code = "authentication"
    retryable = False


class ProviderValidationError(DomainError):
    """Provider rejected a request (e.g. bad symbol, invalid params)."""

    error_code = "provider_validation"
    retryable = False


class MalformedDataError(DomainError):
    """Provider returned data that does not match the normalized contract."""

    error_code = "malformed_data"
    retryable = False


class UnsupportedCapabilityError(DomainError):
    error_code = "unsupported_capability"
    retryable = False


class IdempotencyConflictError(DomainError):
    error_code = "idempotency_conflict"
    retryable = False


class ConfigurationError(DomainError):
    error_code = "configuration"
    retryable = False


class RiskBlockError(DomainError):
    error_code = "risk_block"
    retryable = True


class NotFoundError(DomainError):
    error_code = "not_found"
    retryable = False


class InsufficientDataError(DomainError):
    error_code = "insufficient_data"
    retryable = False


class FatalSystemError(DomainError):
    error_code = "fatal_system"
    retryable = False

    def __init__(self, message: str) -> None:
        super().__init__(message)


ERROR_HTTP_STATUS: dict[str, int] = {
    "provider_unavailable": 502,
    "rate_limited": 429,
    "provider_timeout": 504,
    "authentication": 401,
    "provider_validation": 400,
    "malformed_data": 502,
    "unsupported_capability": 400,
    "idempotency_conflict": 409,
    "configuration": 500,
    "risk_block": 400,
    "not_found": 404,
    "insufficient_data": 422,
    "fatal_system": 500,
    "domain_error": 400,
}


def http_status_for(error: DomainError) -> int:
    return ERROR_HTTP_STATUS.get(error.error_code, 400)
