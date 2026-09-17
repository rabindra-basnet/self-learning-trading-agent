"""strategies domain: pure strategy contract — no provider imports."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel

from app.modules.marketdata.contracts import Candle
from app.modules.signals.contracts import FeatureVector


class SignalDirection(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class StrategyParams(BaseModel):
    model_config = {"extra": "allow"}
    name: str


class Strategy(Protocol):
    """Domain capability — implementations live in slice infrastructure/library."""

    strategy_id: str
    params: StrategyParams

    def evaluate(self, candles: Sequence[Candle], features: Sequence[FeatureVector]) -> SignalDirection: ...


class StrategyStore(Protocol):
    """Outbound port for the strategy catalog. Implementations may be
    code-backed (library) or data-backed (redis/postgres); the manager treats
    them uniformly."""

    async def put(self, strategy: Strategy) -> None: ...

    async def get(self, strategy_id: str) -> Strategy | None: ...

    async def all(self) -> list[Strategy]: ...
