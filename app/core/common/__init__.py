"""Shared pure helpers: Result[T,E], Clock, id generation.

Nothing in this package may import providers, frameworks, or infra technology.
"""

from app.core.common.clock import Clock, FrozenClock, SystemClock
from app.core.common.result import Err, Ok, Result

__all__ = ["Clock", "Err", "FrozenClock", "Ok", "Result", "SystemClock"]
