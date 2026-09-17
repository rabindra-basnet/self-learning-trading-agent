"""Yahoo Finance adapter — implements the MarketDataSource port.

Composes the shared infra tooling (retry, breaker, rate limit, timeout) and
normalizes through `mapping.py`. Thin by design: no business logic lives here.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from functools import partial

from app.core.exceptions.taxonomy import UnsupportedCapabilityError
from app.infrastructure.tooling import CircuitBreaker, Policy, RateLimiter, RetryPolicy
from app.modules.marketdata.domain.entities import Candle, Symbol, Ticker, Timeframe
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.client import YahooRawClient
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.config import YahooConfig
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.mapping import (
    EXCHANGE,
    to_candles,
    to_ticker,
    to_yahoo_symbol,
)

_INTERVALS: dict[Timeframe, str] = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.H1: "1h",
    Timeframe.D1: "1d",
}


class YahooMarketDataSource:
    """MarketDataSource implemented against the public Yahoo chart endpoint."""

    def __init__(self, config: YahooConfig) -> None:
        self._client = YahooRawClient(config)
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
        interval = _INTERVALS.get(timeframe)
        if interval is None:
            raise UnsupportedCapabilityError(
                f"yahoo does not serve {timeframe.value} candles",
                provider=EXCHANGE,
            )
        period1, period2 = _window(since)
        code = to_yahoo_symbol(symbol)
        chart = await self._policy.run(
            lambda: self._client.fetch_chart(code, interval, period1=period1, period2=period2)
        )
        return to_candles(chart, symbol, timeframe, EXCHANGE)[-limit:]

    async def fetch_tickers(self, symbols: Sequence[Symbol]) -> list[Ticker]:
        tickers: list[Ticker] = []
        for symbol in symbols:
            code = to_yahoo_symbol(symbol)
            chart = await self._policy.run(partial(self._client.fetch_chart, code, "1d"))
            tickers.append(to_ticker(chart, symbol, EXCHANGE))
        return tickers

    async def close(self) -> None:
        await self._client.close()


def _window(since: datetime | None) -> tuple[int | None, int | None]:
    if since is None:
        return None, None
    return int(since.timestamp()), int(datetime.now(UTC).timestamp())
