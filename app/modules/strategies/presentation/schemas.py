"""strategies inbound/outbound schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.modules.strategies.domain.entities import StrategyMeta


class EvaluateResponse(BaseModel):
    strategy_id: str
    symbol: str
    timeframe: str
    signal: str


__all__ = ["EvaluateResponse", "StrategyMeta"]
