"""Shared HTTP transport for vendor clients (docs/INTEGRATION-ARCHITECTURE.md §7).

Owns the HTTP -> domain error translation so every boundary reports failures
through the same taxonomy and no `httpx` exception ever crosses a provider
boundary. Vendor clients compose this and only see primitive JSON payloads.
"""

from __future__ import annotations

from typing import Any

import httpx
from app.core.exceptions.taxonomy import (
    AuthenticationError,
    DomainError,
    MalformedDataError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
    RateLimitedError,
)


def map_http_error(status: int, provider: str, message: str = "") -> DomainError:
    detail = f"{provider} http {status}"
    if message:
        detail = f"{detail}: {message}"
    if status in (401, 403):
        return AuthenticationError(detail, provider=provider)
    if status == 429:
        return RateLimitedError(detail, provider=provider)
    if status in (408, 504):
        return ProviderTimeoutError(detail, provider=provider)
    if 500 <= status < 600:
        return ProviderUnavailableError(detail, provider=provider)
    return ProviderValidationError(detail, provider=provider)


class JsonHttpClient:
    """Thin async JSON transport: raw payloads only, errors normalized."""

    def __init__(
        self,
        base_url: str,
        *,
        provider: str,
        timeout_sec: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._provider = provider
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_sec, headers=headers)

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = await self._client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"{self._provider} request timed out",
                provider=self._provider,
                cause=exc,
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(
                f"{self._provider} transport error",
                provider=self._provider,
                cause=exc,
            ) from exc
        if response.status_code >= 400:
            raise map_http_error(response.status_code, self._provider, response.text[:200])
        try:
            return response.json()
        except ValueError as exc:
            raise MalformedDataError(
                f"{self._provider} returned a non-JSON payload",
                provider=self._provider,
                cause=exc,
            ) from exc

    async def aclose(self) -> None:
        await self._client.aclose()
