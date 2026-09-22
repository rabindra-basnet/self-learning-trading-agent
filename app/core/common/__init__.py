"""Shared pure helpers: Result[T, E], ports, and deterministic test helpers.

Nothing in this package may import providers, frameworks, or infrastructure.
"""

from app.core.common.clock import Clock, FrozenClock
from app.core.common.result import Err, Ok, Result

__all__ = ["Clock", "Err", "FrozenClock", "Ok", "Result"]
