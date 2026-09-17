"""Kraken raw client — HTTP specifics confined here.

Exposes `result` payloads only; the `error` array never leaves this module
unmapped.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.exceptions.taxonomy import MalformedDataError
from app.infrastructure.tooling.http import JsonHttpClient
from app.modules.marketdata.infrastructure.providers.exchange.kraken.config import KrakenConfig
from app.modules.marketdata.infrastructure.providers.exchange.kraken.dtos import KrakenResponse
from app.modules.marketdata.infrastructure.providers.exchange.kraken.errors import (
    handle_kraken_errors,
)

_PROVIDER = "kraken"


class KrakenRawClient:
    def __init__(self, config: KrakenConfig) -> None:
        self._http = JsonHttpClient(
            config.base_url,
            provider=_PROVIDER,
            timeout_sec=config.timeout_sec,
            headers={"User-Agent": config.user_agent, "Accept": "application/json"},
        )

    async def fetch_ohlc(
        self,
        pair: str,
        interval: int,
        since_ms: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"pair": pair, "interval": interval}
        if since_ms is not None:
            params["since"] = since_ms
        return await self._request("/0/public/OHLC", params)

    async def fetch_ticker(self, pair: str) -> dict[str, Any]:
        return await self._request("/0/public/Ticker", {"pair": pair})

    async def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = await self._http.get_json(path, params)
        try:
            response = KrakenResponse.model_validate(payload)
        except ValidationError as exc:
            raise MalformedDataError(
                f"kraken payload did not match the expected schema: {exc}",
                provider=_PROVIDER,
                cause=exc,
            ) from exc
        if response.error:
            raise handle_kraken_errors(response.error)
        return response.result

    async def close(self) -> None:
        await self._http.aclose()
