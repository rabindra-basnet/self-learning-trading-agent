"""Yahoo payload errors -> domain error mapping (boundary rule §9).

Yahoo reports failures inside a 200 response (`chart.error`), so payload-level
error codes are mapped here rather than in the shared HTTP helper.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.core.exceptions.taxonomy import (
    AuthenticationError,
    DomainError,
    MalformedDataError,
    ProviderUnavailableError,
    ProviderValidationError,
    RateLimitedError,
)

_PROVIDER = "yahoo"
_AUTH_CODES = frozenset({"401", "403"})
_REQUEST_CODES = frozenset({"400", "404", "422"})


def handle_yahoo_error(error: Mapping[str, Any]) -> DomainError:
    code = str(error.get("code", "")).strip()
    description = str(error.get("description") or "yahoo request failed")
    if code in _AUTH_CODES:
        return AuthenticationError(description, provider=_PROVIDER)
    if code == "429":
        return RateLimitedError(description, provider=_PROVIDER)
    if code in _REQUEST_CODES:
        return ProviderValidationError(description, provider=_PROVIDER)
    return ProviderUnavailableError(f"yahoo error {code or '?'}: {description}", provider=_PROVIDER)


def handle_yahoo_validation_error(exc: ValidationError) -> DomainError:
    return MalformedDataError(
        f"yahoo payload did not match the expected schema: {exc}",
        provider=_PROVIDER,
        cause=exc,
    )
