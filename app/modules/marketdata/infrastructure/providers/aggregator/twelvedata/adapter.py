"""Twelve Data adapter — implements the MarketDataSource port."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from functools import partial

from app.core.exceptions.taxonomy import UnsupportedCapabilityError
from app.infrastructure.tooling import CircuitBreaker, Policy, RateLimiter, RetryPolicy
from app.modules.marketdata.domain.entities import Candle, Symbol, Ticker, Timeframe
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.client import (
    TwelveDataRawClient,
)
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.config import (
    TwelveDataConfig,
)
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.mapping import (
    EXCHANGE,
    to_candles,
    to_ticker,
)

_INTERVALS: dict[Timeframe, str] = {
    Timeframe.M1: "1min",
    Timeframe.M5: "5min",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1day",
}
_DAILY = frozenset({Timeframe.D1})
_MAX_OUTPUT = 5000


class TwelveDataMarketDataSource:
    """MarketDataSource implemented against the Twelve Data REST API."""

    def __init__(self, config: TwelveDataConfig) -> None:
        self._client = TwelveDataRawClient(config)
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
                f"twelve data does not serve {timeframe.value} candles",
                provider=EXCHANGE,
            )
        start_date = _stamp(since, timeframe) if since else None
        series = await self._policy.run(
            lambda: self._client.fetch_time_series(
                symbol.code,
                interval,
                outputsize=min(limit, _MAX_OUTPUT),
                start_date=start_date,
            )
        )
        return to_candles(series.values, symbol, timeframe, EXCHANGE)[-limit:]

    async def fetch_tickers(self, symbols: Sequence[Symbol]) -> list[Ticker]:
        observed_at = datetime.now(UTC)
        tickers: list[Ticker] = []
        for symbol in symbols:
            code = symbol.code
            quote = await self._policy.run(partial(self._client.fetch_quote, code))
            tickers.append(to_ticker(quote, symbol, observed_at, EXCHANGE))
        return tickers

    async def close(self) -> None:
        await self._client.close()


def _stamp(moment: datetime, timeframe: Timeframe) -> str:
    return moment.strftime("%Y-%m-%d") if timeframe in _DAILY else moment.strftime("%Y-%m-%d %H:%M:%S")
