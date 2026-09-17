"""strategies domain: identity/events (pure)."""

from __future__ import annotations

from pydantic import BaseModel

from app.core.messaging.bus import DomainEvent


class StrategyMeta(BaseModel):
    strategy_id: str
    name: str
    params: dict[str, float | str | bool]


class StrategyRegistered(DomainEvent):
    strategy_id: str
    name: str
