"""signals domain events."""

from __future__ import annotations

from app.core.messaging.bus import DomainEvent


class FeatureComputed(DomainEvent):
    symbol: str
    timeframe: str
    feature_count: int
    vector_count: int
