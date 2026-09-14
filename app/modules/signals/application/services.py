"""signals application service — pure orchestration (no pandas, no providers)."""

from __future__ import annotations

from app.core.messaging.bus import EventBus
from app.modules.marketdata.contracts import Candle
from app.modules.signals.domain.events import FeatureComputed
from app.modules.signals.domain.ports import FeatureComputer


class FeatureService:
    def __init__(self, computer: FeatureComputer, bus: EventBus) -> None:
        self._computer = computer
        self._bus = bus

    async def compute(self, candles: list[Candle], features: list[str] | None = None) -> list:
        vectors = self._computer.compute(candles, features)
        if vectors:
            first = vectors[0]
            await self._bus.publish(
                FeatureComputed(
                    symbol=first.symbol,
                    timeframe=first.timeframe,
                    feature_count=len(first.features),
                    vector_count=len(vectors),
                )
            )
        return vectors
