"""backtest domain ports."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from app.modules.marketdata.contracts import Candle, Symbol, Timeframe
from app.modules.signals.contracts import FeatureVector


class BacktestDataStore(Protocol):
    async def query_range(
        self, symbol: Symbol, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]: ...


class BacktestFeatureComputer(Protocol):
    def compute(self, candles: Sequence[Candle], features: list[str] | None = None) -> list[FeatureVector]: ...
