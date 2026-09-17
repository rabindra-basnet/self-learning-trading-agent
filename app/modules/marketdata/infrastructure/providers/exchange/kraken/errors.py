"""Kraken payload errors -> domain error mapping (boundary rule §9).

Kraken returns HTTP 200 with a non-empty `error` array; each string is mapped to
exactly one domain error.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.exceptions.taxonomy import (
    AuthenticationError,
    DomainError,
    ProviderUnavailableError,
    ProviderValidationError,
    RateLimitedError,
)

_PROVIDER = "kraken"


def handle_kraken_errors(errors: Sequence[str]) -> DomainError:
    joined = "; ".join(errors) or "unknown kraken error"
    for error in errors:
        lowered = error.lower()
        if "rate limit" in lowered or "too many requests" in lowered:
            return RateLimitedError(joined, provider=_PROVIDER)
        if "invalid key" in lowered or "invalid signature" in lowered or "invalid nonce" in lowered:
            return AuthenticationError(joined, provider=_PROVIDER)
        if "invalid arguments" in lowered or "unknown asset pair" in lowered or "invalid asset pair" in lowered:
            return ProviderValidationError(joined, provider=_PROVIDER)
    return ProviderUnavailableError(joined, provider=_PROVIDER)
