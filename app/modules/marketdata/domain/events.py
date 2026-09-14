"""marketdata domain events (normalized)."""

from __future__ import annotations

from app.core.messaging.bus import DomainEvent
from app.modules.marketdata.domain.entities import Candle, Symbol


class CandleReceived(DomainEvent):
    symbol: Symbol
    timeframe: str
    candles: list[Candle]
