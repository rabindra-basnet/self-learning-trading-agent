"""In-process strategy catalog adapter — builtins only.

Strategies are code objects; this store maps each strategy_id to its singleton
Strategy instance so runners can resolve names.
"""

from __future__ import annotations

from typing import Any

from app.modules.strategies.domain.ports import Strategy
from app.modules.strategies.infrastructure.providers.strategies.library import BUILTIN_STRATEGIES


class StrategyLibraryStore:
    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}

    async def __connect__(self) -> None:
        self._strategies = dict(BUILTIN_STRATEGIES)

    async def __disconnect__(self) -> None:
        pass

    def register(self, strategy: Strategy) -> None:
        self._strategies[strategy.strategy_id] = strategy

    def get(self, strategy_id: str) -> Strategy | None:
        return self._strategies.get(strategy_id)

    def list_meta(self) -> list[Any]:
        from app.modules.strategies.domain.entities import StrategyMeta

        return [
            StrategyMeta(
                strategy_id=sid,
                name=s.params.name,
                params=s.params.model_dump(),
            )
            for sid, s in self._strategies.items()
        ]
