"""Binance SDK exception → domain error mapping (boundary rule §9)."""

from __future__ import annotations

import ccxt

from app.core.exceptions.taxonomy import (
    AuthenticationError,
    DomainError,
    MalformedDataError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
    RateLimitedError,
)


def _is_any(exc: Exception, *types: type[BaseException]) -> bool:
    return isinstance(exc, types)


def handle_binance_error(exc: Exception) -> DomainError:
    if _is_any(exc, ccxt.RateLimitExceeded):
        return RateLimitedError("binance rate limit exceeded", provider="binance", cause=exc)
    if _is_any(exc, ccxt.AuthenticationError):
        return AuthenticationError("binance authentication failed", provider="binance", cause=exc)
    if _is_any(exc, ccxt.RequestTimeout):
        return ProviderTimeoutError("binance request timed out", provider="binance", cause=exc)
    if _is_any(
        exc,
        ccxt.NetworkError,
        ccxt.ExchangeNotAvailable,
        ccxt.OnMaintenance,
        ccxt.DDoSProtection,
        ccxt.ExchangeError,
    ):
        return ProviderUnavailableError("binance unavailable", provider="binance", cause=exc)
    if _is_any(exc, ccxt.BadRequest, ccxt.BadSymbol, ccxt.InvalidOrder, ccxt.ArgumentsRequired):
        return ProviderValidationError(f"binance rejected request: {exc}", provider="binance", cause=exc)
    if isinstance(exc, ValueError):
        return MalformedDataError(f"binance payload error: {exc}", provider="binance", cause=exc)
    return ProviderUnavailableError(f"unexpected binance error: {exc!r}", provider="binance", cause=exc)
