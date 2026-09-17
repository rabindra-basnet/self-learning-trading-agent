"""Rust-flavoured Result[T, E] — domain-safe error channel.

It is the ONLY error-propagation type allowed in use-cases (AGENTS.md). Providers
map their own failures here, never leaking vendor types.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
E = TypeVar("E")
F = TypeVar("F")


@dataclass(frozen=True, slots=True)
class Result[T, E]:
    _value: T | None = None
    _error: E | None = None

    @property
    def is_ok(self) -> bool:
        return self._error is None

    @property
    def is_err(self) -> bool:
        return not self.is_ok

    def ok_value(self) -> T:
        if self._value is not None:
            return self._value
        raise ValueError(f"Result is an error: {self._error!r}")

    def error_value(self) -> E:
        if self._error is not None:
            return self._error
        raise ValueError("Result is an ok value")

    def map_err(self, fn: Callable[[E], F]) -> Result[T, F]:
        if self._error is None:
            return Result(_value=self._value)
        return Result(_error=fn(self._error))

    def __repr__(self) -> str:
        if self.is_ok:
            return f"Ok({self._value!r})"
        return f"Err({self._error!r})"


def Ok[T, E](value: T) -> Result[T, E]:
    return Result(_value=value)


def Err[T, E](error: E) -> Result[T, E]:
    return Result(_error=error)
