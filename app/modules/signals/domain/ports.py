"""signals domain: ports (provider-free, capability-only)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.marketdata.contracts import Candle
from app.modules.signals.domain.entities import FeatureVector


class FeatureComputer(Protocol):
    """Provider-independent compute contract — implementation lives in infrastructure."""

    def compute(self, candles: Sequence[Candle], features: list[str] | None = None) -> list[FeatureVector]: ...
