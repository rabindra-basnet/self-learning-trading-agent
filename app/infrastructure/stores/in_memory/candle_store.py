"""In-memory CandleStore — implements the CandleStore port (sorted containers)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.modules.marketdata.domain.entities import Candle, Symbol, Timeframe


class InMemoryCandleStore:
    def __init__(self) -> None:
        self._store: dict[tuple[str, str], list[Candle]] = {}

    async def append(self, candles: Sequence[Candle]) -> int:
        appended = 0
        for candle in candles:
            key = (candle.symbol.code, candle.timeframe.value)
            bin = self._store.setdefault(key, [])
            if not any(c.opened_at == candle.opened_at for c in bin):
                bin.append(candle)
                bin.sort(key=lambda c: c.opened_at)
                appended += 1
        return appended

    async def query_range(self, symbol: Symbol, timeframe: Timeframe, start: datetime, end: datetime) -> list[Candle]:
        return [c for c in self._store.get((symbol.code, timeframe.value), []) if start <= c.opened_at <= end]

    async def latest(self, symbol: Symbol, timeframe: Timeframe, n: int = 100) -> list[Candle]:
        return self._store.get((symbol.code, timeframe.value), [])[-n:]
