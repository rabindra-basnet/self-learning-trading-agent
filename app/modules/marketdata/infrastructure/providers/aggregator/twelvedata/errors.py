"""Twelve Data payload errors -> domain error mapping (boundary rule §9).

Twelve Data reports failures inside a 200 response with a numeric `code`.
"""

from __future__ import annotations

from app.core.exceptions.taxonomy import (
    AuthenticationError,
    DomainError,
    ProviderUnavailableError,
    ProviderValidationError,
    RateLimitedError,
)

_PROVIDER = "twelvedata"
_AUTH_CODES = frozenset({401, 403})


def handle_twelvedata_error(code: int | None, message: str | None) -> DomainError:
    detail = message or "twelve data request failed"
    if code in _AUTH_CODES:
        return AuthenticationError(detail, provider=_PROVIDER)
    if code == 429:
        return RateLimitedError(detail, provider=_PROVIDER)
    if code is not None and code >= 500:
        return ProviderUnavailableError(f"twelve data error {code}: {detail}", provider=_PROVIDER)
    if code is not None:
        return ProviderValidationError(f"twelve data error {code}: {detail}", provider=_PROVIDER)
    return ProviderUnavailableError(detail, provider=_PROVIDER)
