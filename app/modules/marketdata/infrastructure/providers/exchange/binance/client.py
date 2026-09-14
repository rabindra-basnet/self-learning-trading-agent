"""Binance raw client — SDK/API specifics are confined to this file.

Exposes only primitive payloads (`RawKline`, dicts) for `mapping.py` to normalize.
"""

from __future__ import annotations

from typing import Any

import ccxt.async_support as ccxt

from app.modules.marketdata.infrastructure.providers.exchange.binance.config import BinanceConfig
from app.modules.marketdata.infrastructure.providers.exchange.binance.errors import (
    handle_binance_error,
)


class BinanceRawClient:
    def __init__(self, config: BinanceConfig) -> None:
        self._config = config
        self._exchange: ccxt.binance = ccxt.binance(
            {
                "apiKey": config.api_key.get_secret_value() or None,
                "secret": config.api_secret.get_secret_value() or None,
                "urls": {"api": {"public": config.base_url}},
                "enableRateLimit": False,
                "timeout": int(config.timeout_sec * 1000),
            }
        )

    async def fetch_ohlcv(
        self,
        symbol_code: str,
        timeframe: str,
        since_ms: int | None,
        limit: int,
    ) -> list[list[Any]]:
        try:
            rows = await self._exchange.fetch_ohlcv(symbol_code, timeframe=timeframe, since=since_ms, limit=limit)
        except Exception as exc:
            raise handle_binance_error(exc) from exc
        return [list(row) for row in rows]

    async def fetch_tickers_raw(self, symbol_codes: list[str]) -> dict[str, dict[str, Any]]:
        try:
            tickers = await self._exchange.fetch_tickers(symbol_codes or None)
        except Exception as exc:
            raise handle_binance_error(exc) from exc
        return {code: dict(entry) for code, entry in tickers.items()}

    async def close(self) -> None:
        try:
            await self._exchange.close()
        except Exception:
            return None
