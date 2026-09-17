"""Kraken adapter — implements the MarketDataSource port."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from functools import partial
from typing import Any

from app.infrastructure.tooling import CircuitBreaker, Policy, RateLimiter, RetryPolicy
from app.modules.marketdata.domain.entities import Candle, Symbol, Ticker, Timeframe
from app.modules.marketdata.infrastructure.providers.exchange.kraken.client import KrakenRawClient
from app.modules.marketdata.infrastructure.providers.exchange.kraken.config import KrakenConfig
from app.modules.marketdata.infrastructure.providers.exchange.kraken.mapping import (
    EXCHANGE,
    first_entry,
    to_candles,
    to_kraken_pair,
    to_ticker,
)

_INTERVALS: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 5,
    Timeframe.H1: 60,
    Timeframe.H4: 240,
    Timeframe.D1: 1440,
}


class KrakenMarketDataSource:
    """MarketDataSource implemented against Kraken's public endpoints."""

    def __init__(self, config: KrakenConfig) -> None:
        self._client = KrakenRawClient(config)
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
        pair = to_kraken_pair(symbol)
        since_ms = int(since.timestamp() * 1000) if since else None
        result = await self._policy.run(lambda: self._client.fetch_ohlc(pair, _INTERVALS[timeframe], since_ms))
        rows: Sequence[Sequence[Any]] = result.get(pair, first_entry(result))
        return to_candles(rows, symbol, timeframe, EXCHANGE)[-limit:]

    async def fetch_tickers(self, symbols: Sequence[Symbol]) -> list[Ticker]:
        observed_at = datetime.now(UTC)
        tickers: list[Ticker] = []
        for symbol in symbols:
            pair = to_kraken_pair(symbol)
            result = await self._policy.run(partial(self._client.fetch_ticker, pair))
            tickers.append(to_ticker(first_entry(result), symbol, observed_at, EXCHANGE))
        return tickers

    async def close(self) -> None:
        await self._client.close()
