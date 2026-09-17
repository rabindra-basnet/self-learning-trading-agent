"""signals contracts."""

from datetime import datetime
from typing import Protocol

from app.modules.marketdata.contracts import Candle, Symbol, Timeframe
from app.modules.signals.domain.entities import FeatureVector
from app.modules.signals.domain.events import FeatureComputed


class CandleQueryPort(Protocol):
    """Cross-slice seam: satisfied by marketdata's CandleQueryService at the
    composition root, so the signals slice reads candles through a port instead
    of importing another slice's application layer."""

    async def range(self, symbol: Symbol, timeframe: Timeframe, start: datetime, end: datetime) -> list[Candle]: ...


__all__ = ["CandleQueryPort", "FeatureComputed", "FeatureVector"]
