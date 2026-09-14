"""marketdata ports — provider-independent capability contracts."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from app.core.common.clock import Clock
from app.modules.marketdata.domain.entities import Candle, Symbol, Ticker, Timeframe


class MarketDataSource(Protocol):
    """Fetch normalized candles/tickers regardless of the underlying exchange."""

    async def fetch_candles(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        *,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]: ...

    async def fetch_tickers(self, symbols: Sequence[Symbol]) -> list[Ticker]: ...


class CandleStore(Protocol):
    async def append(self, candles: Sequence[Candle]) -> int: ...

    async def query_range(
        self, symbol: Symbol, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]: ...

    async def latest(self, symbol: Symbol, timeframe: Timeframe, n: int = 100) -> list[Candle]: ...


class TimeSource(Clock):
    """Capability alias so services depend on the capability name, not core typing."""
