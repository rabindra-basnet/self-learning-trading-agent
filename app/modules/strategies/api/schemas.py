"""strategies inbound/outbound schemas."""

from typing import Any

from pydantic import BaseModel


class StrategyMeta(BaseModel):
    strategy_id: str
    name: str
    params: dict[str, Any]


class EvaluateResponse(BaseModel):
    strategy_id: str
    symbol: str
    timeframe: str
    signal: str