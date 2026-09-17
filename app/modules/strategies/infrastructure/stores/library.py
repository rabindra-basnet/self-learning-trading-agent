"""In-process strategy catalog adapter — builtins only.

Strategies are code objects; this store maps each strategy_id to its singleton
implementation so `evaluate()` can run in-process without a round-trip.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.modules.strategies.domain.ports import Strategy


class StrategyLibraryStore:
    def __init__(self, strategies: Mapping[str, Strategy]) -> None:
        self._strategies = dict(strategies)

    async def put(self, strategy: Strategy) -> None:
        self._strategies[strategy.strategy_id] = strategy

    async def get(self, strategy_id: str) -> Strategy | None:
        return self._strategies.get(strategy_id)

    async def all(self) -> list[Strategy]:
        return list(self._strategies.values())
