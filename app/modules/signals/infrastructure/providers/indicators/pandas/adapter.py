"""signals infrastructure: pandas feature computer (third-party confined here)."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
from app.modules.marketdata.contracts import Candle
from app.modules.signals.domain.entities import FeatureVector


class PandasFeatureComputer:
    async def __connect__(self) -> None:
        pass

    async def __disconnect__(self) -> None:
        pass

    """FeatureComputer implemented with pandas-ta style indicator math."""

    def compute(self, candles: Sequence[Candle], features: list[str] | None = None) -> list[FeatureVector]:
        if not candles:
            return []
        frame = pd.DataFrame(
            {
                "opened_at": [c.opened_at for c in candles],
                "open": [float(c.open) for c in candles],
                "high": [float(c.high) for c in candles],
                "low": [float(c.low) for c in candles],
                "close": [float(c.close) for c in candles],
                "volume": [float(c.volume) for c in candles],
            }
        ).sort_values("opened_at")
        close = frame["close"]

        frame["sma10"] = close.rolling(10).mean()
        frame["sma20"] = close.rolling(20).mean()
        frame["ema12"] = close.ewm(span=12, adjust=False).mean()
        frame["ema26"] = close.ewm(span=26, adjust=False).mean()
        frame["rsi14"] = _rsi(close, 14)
        frame["macd"] = frame["ema12"] - frame["ema26"]
        frame["bb_upper"], frame["bb_lower"], frame["bb_mid"] = _bollinger(close, 20, 2.0)
        frame["volume_ma20"] = frame["volume"].rolling(20).mean()

        requested = {f for f in features} if features else set(frame.columns)
        vectors: list[FeatureVector] = []
        for _, row in frame.iterrows():
            feats = {k: _to_float(v) for k, v in row.items() if k in requested and _to_float(v) is not None}
            vectors.append(
                FeatureVector(
                    symbol=candles[0].symbol.code,
                    timeframe=candles[0].timeframe.value,
                    timestamp=row["opened_at"],
                    features=feats,
                )
            )
        return vectors


def _to_float(value: object) -> float | None:
    try:
        import math

        result = float(value)  # type: ignore[arg-type]
        return None if math.isnan(result) or math.isinf(result) else result
    except (TypeError, ValueError):
        return None


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("inf"))
    return 100.0 - (100.0 / (1.0 + rs))


def _bollinger(series: pd.Series, window: int, k: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = series.rolling(window).mean()
    std = series.rolling(window).std()
    return mid + k * std, mid - k * std, mid
