"""strategy manager: register, list, evaluate."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.modules.strategies.api.schemas import StrategyMeta
from app.modules.strategies.domain.ports import SignalDirection, Strategy


class StrategyManager:
    """Owns the built-in strategy library."""

    def __init__(self, strategies: Mapping[str, Strategy]) -> None:
        self._strategies = dict(strategies)

    def list(self) -> list[StrategyMeta]:
        return [
            StrategyMeta(strategy_id=s.strategy_id, name=s.params.name, params={})
            for s in self._strategies.values()
        ]

    def evaluate(self, strategy_id: str, candles: Sequence[Any], features: Sequence[Any]) -> SignalDirection:
        return self._strategies[strategy_id].evaluate(candles, features)