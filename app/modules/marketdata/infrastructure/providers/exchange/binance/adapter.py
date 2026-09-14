"""Binance boundary adapter — implements the MarketDataSource port.

Composes RetryPolicy, CircuitBreaker, RateLimiter, timeout (infra tooling) and
maps payloads through `mapping.py`. Nothing in this module can leak outside the
boundary into domain/application.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.infrastructure.tooling import CircuitBreaker, Policy, RateLimiter, RetryPolicy
from app.modules.marketdata.domain.entities import Candle, Symbol, Ticker, Timeframe
from app.modules.marketdata.infrastructure.providers.exchange.binance.client import BinanceRawClient
from app.modules.marketdata.infrastructure.providers.exchange.binance.config import BinanceConfig
from app.modules.marketdata.infrastructure.providers.exchange.binance.dtos import RawKline
from app.modules.marketdata.infrastructure.providers.exchange.binance.mapping import (
    to_candle,
    to_ticker,
)

_EXCHANGE = "binance"


class BinanceMarketDataSource:
    """MarketDataSource implemented against Binance via ccxt."""

    def __init__(self, config: BinanceConfig) -> None:
        self._config = config
        self._client = BinanceRawClient(config)
        self._policy = Policy(
            retry=RetryPolicy(retries=config.retries, backoff_base_sec=config.backoff_base_sec),
            breaker=CircuitBreaker(failure_threshold=config.circuit_open_after),
            limiter=RateLimiter(per_second=config.rate_per_sec),
            timeout_sec=config.timeout_sec,
        )

    async def fetch_candles(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        *,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]:
        symbol_code = symbol.code.upper()
        since_ms = int(since.timestamp() * 1000) if since else None
        return await self._policy.run(
            lambda: self._fetch_and_map_ohlcv(symbol, symbol_code, timeframe, since_ms, limit)
        )

    async def fetch_tickers(self, symbols: Sequence[Symbol]) -> list[Ticker]:
        codes = [s.code.upper() for s in symbols]
        raw = await self._policy.run(lambda: self._client.fetch_tickers_raw(codes))
        by_code = {s.code.upper(): s for s in symbols}
        return [to_ticker(raw[code], by_code[code], _EXCHANGE) for code in codes if code in raw]

    async def _fetch_and_map_ohlcv(
        self,
        symbol: Symbol,
        symbol_code: str,
        timeframe: Timeframe,
        since_ms: int | None,
        limit: int,
    ) -> list[Candle]:
        rows = await self._client.fetch_ohlcv(symbol_code, timeframe.value, since_ms, limit)
        candles = [to_candle(RawKline.of(row), symbol, timeframe, _EXCHANGE) for row in rows if row]
        return self._sort_unique(candles)

    @staticmethod
    def _sort_unique(candles: list[Candle]) -> list[Candle]:
        seen: set[int] = set()
        out: list[Candle] = []
        for c in sorted(candles, key=lambda c: c.opened_at):
            ts = int(c.opened_at.timestamp())
            if ts not in seen:
                seen.add(ts)
                out.append(c)
        return out

    async def close(self) -> None:
        await self._client.close()
