"""Composable reliability policies for integration boundaries.

A boundary composes retry+backoff, circuit breaker, rate limiting and timeout
exactly as its vendor requires — without leaking policy into the domain.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

from app.core.exceptions.taxonomy import DomainError, ProviderUnavailableError

T = TypeVar("T")
Call = Callable[[], Awaitable[T]]


@dataclass(slots=True)
class RetryPolicy:
    retries: int = 3
    backoff_base_sec: float = 0.3
    max_backoff_sec: float = 8.0
    jitter: bool = True
    _attempts: int = field(default=0, init=False)

    async def run(self, fn: Call[T]) -> T:
        self._attempts = 0
        while True:
            self._attempts += 1
            try:
                return await fn()
            except DomainError as exc:
                if not exc.retryable or self._attempts >= self.retries:
                    raise
                await self._sleep(self._attempts)
            except Exception as exc:
                raise ProviderUnavailableError("unexpected provider failure", cause=exc) from exc

    async def _sleep(self, attempt: int) -> None:
        backoff = min(self.backoff_base_sec * (2 ** (attempt - 1)), self.max_backoff_sec)
        if self.jitter:
            backoff *= 0.5 + random.random()
        await asyncio.sleep(backoff)


@dataclass(slots=True)
class RateLimiter:
    per_second: float = 5.0
    _last: float = field(default=0.0, init=False)

    async def acquire(self) -> None:
        if self.per_second <= 0:
            return
        now = asyncio.get_event_loop().time()
        wait = self._last + (1.0 / self.per_second) - now
        if wait > 0:
            await asyncio.sleep(wait)
        self._last = asyncio.get_event_loop().time()


@dataclass(slots=True)
class CircuitBreaker:
    failure_threshold: int = 5
    _failures: int = field(default=0, init=False)
    _open: bool = field(default=False, init=False)

    async def run(self, fn: Call[T]) -> T:
        if self._open:
            raise ProviderUnavailableError("circuit_open", provider="tooling")
        try:
            result = await fn()
            self._failures = 0
            return result
        except DomainError:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._open = True
            raise

    def reset(self) -> None:
        self._open = False
        self._failures = 0


@dataclass(slots=True)
class Policy:
    """Composition of retry ⊗ breaker ⊗ ratelimit for one call."""

    retry: RetryPolicy | None = None
    breaker: CircuitBreaker | None = None
    limiter: RateLimiter | None = None
    timeout_sec: float | None = None

    async def run(self, fn: Call[T]) -> T:
        breaker = self.breaker
        retry = self.retry

        async def _guarded() -> T:
            if self.timeout_sec:
                return await asyncio.wait_for(fn(), timeout=self.timeout_sec)
            return await fn()

        async def _limited() -> T:
            if self.limiter:
                await self.limiter.acquire()
            return await _guarded()

        async def _core() -> T:
            if breaker is None:
                return await _limited()
            return await breaker.run(_limited)

        if retry is None:
            return await _core()
        return await retry.run(_core)
