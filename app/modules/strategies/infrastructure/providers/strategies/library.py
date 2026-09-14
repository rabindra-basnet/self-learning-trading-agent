"""Built-in strategy implementations (capacity layer, provider-free).

Frameworks can wrap these; the library itself only depends on domain models.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.marketdata.contracts import Candle
from app.modules.signals.contracts import FeatureVector
from app.modules.strategies.domain.ports import SignalDirection, Strategy, StrategyParams


class SmaCrossStrategy:
    strategy_id = "sma_cross"
    short = 10
    long = 20

    @property
    def params(self) -> StrategyParams:
        return StrategyParams(name="SMA Cross", short=self.short, long=self.long)

    def evaluate(self, candles: Sequence[Candle], features: Sequence[FeatureVector]) -> SignalDirection:
        key_short = f"sma{self.short}"
        key_long = f"sma{self.long}"
        data = features or []
        short_vals = [fv.features.get(key_short) for fv in data if key_short in fv.features]
        long_vals = [fv.features.get(key_long) for fv in data if key_long in fv.features]
        if len(short_vals) < 2 or len(long_vals) < 2:
            return SignalDirection.HOLD
        if short_vals[-1] > long_vals[-1] and short_vals[-2] <= long_vals[-2]:
            return SignalDirection.BUY
        if short_vals[-1] < long_vals[-1] and short_vals[-2] >= long_vals[-2]:
            return SignalDirection.SELL
        return SignalDirection.HOLD


class RsiMeanReversionStrategy:
    strategy_id = "rsi_reversion"
    oversold = 30.0
    overbought = 70.0

    @property
    def params(self) -> StrategyParams:
        return StrategyParams(name="RSI Mean Reversion", oversold=self.oversold, overbought=self.overbought)

    def evaluate(self, candles: Sequence[Candle], features: Sequence[FeatureVector]) -> SignalDirection:
        rsi_vals = [fv.features["rsi14"] for fv in features if "rsi14" in fv.features]
        if not rsi_vals:
            return SignalDirection.HOLD
        rsi = rsi_vals[-1]
        if rsi <= self.oversold:
            return SignalDirection.BUY
        if rsi >= self.overbought:
            return SignalDirection.SELL
        return SignalDirection.HOLD


_BUILTINS: dict[str, Strategy] = {
    SmaCrossStrategy.strategy_id: SmaCrossStrategy(),
    RsiMeanReversionStrategy.strategy_id: RsiMeanReversionStrategy(),
}


def builtin_strategies() -> dict[str, Strategy]:
    return dict(_BUILTINS)
