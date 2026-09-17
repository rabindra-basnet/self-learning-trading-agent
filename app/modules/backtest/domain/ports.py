"""backtest domain ports."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

from app.core.common.result import Result
from app.core.exceptions.taxonomy import DomainError
from app.modules.marketdata.contracts import Candle, Symbol, Timeframe
from app.modules.signals.contracts import FeatureVector
from app.modules.strategies.contracts import SignalDirection, Strategy


class BacktestDataStore(Protocol):
    async def query_range(
        self, symbol: Symbol, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]: ...


class BacktestFeatureComputer(Protocol):
    def compute(self, candles: Sequence[Candle], features: list[str] | None = None) -> list[FeatureVector]: ...


class StrategyGateway(Protocol):
    """Cross-slice seam: resolved as the strategy slice's StrategyManager at the
    composition root. Typed only through strategies.contracts so the backtest
    slice never imports another slice's internals."""

    async def get_strategy(self, strategy_id: str) -> Strategy | None: ...

    async def evaluate(
        self, strategy_id: str, candles: Sequence[Any], features: Sequence[Any]
    ) -> Result[SignalDirection, DomainError]: ...
