"""Built-in strategy implementations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.modules.strategies.domain.ports import SignalDirection, Strategy, StrategyParams


class SmaCross(Strategy):
    strategy_id = "sma_cross"
    params = StrategyParams(name="sma_cross")
    short = 10
    long = 20

    def evaluate(self, candles: Sequence[Any], features: Sequence[Any]) -> SignalDirection:
        return SignalDirection.HOLD


class RsiMeanReversion(Strategy):
    strategy_id = "rsi_reversion"
    params = StrategyParams(name="rsi_reversion")

    def evaluate(self, candles: Sequence[Any], features: Sequence[Any]) -> SignalDirection:
        return SignalDirection.HOLD


BUILTIN_STRATEGIES: dict[str, Strategy] = {
    SmaCross.strategy_id: SmaCross(),
    RsiMeanReversion.strategy_id: RsiMeanReversion(),
}