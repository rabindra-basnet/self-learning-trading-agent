"""Asyncio event-loop runner for the improve-until-plateau loop.

Each *round* runs a candidate step through the app container, measures a single
numeric metric, and promotes only if the metric improved over the best so far.
The loop keeps going "round until the app stops getting better": after
`max_stale_rounds` consecutive non-improving rounds it declares a plateau,
stops, and exits. Drive it with:

    uv run python -m app.workers.runner

The default step backtests a champion strategy and returns its win rate; swap
the step (or the whole loop) for the real `selfimprovement` slice logic when
S5 lands. The loop is framework-only: it touches existing container services,
never third-party SDKs, and never overrides the risk manager.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from app.api.di import build_container, initialize, shutdown
from app.core.config.settings import get_settings
from app.core.container import Container
from app.core.logging.setup import get_logger
from app.modules.backtest.application.engine import BacktestEngine
from app.modules.backtest.domain.entities import BacktestConfig
from app.modules.marketdata.application.services import CandleQueryService
from app.modules.marketdata.domain.entities import Symbol, Timeframe
from app.modules.strategies.application.manager import StrategyManager

logger = get_logger("app.workers.runner")

RoundStep = Callable[[Container, "LoopConfig"], Awaitable[float]]


@dataclass(frozen=True)
class LoopConfig:
    """Loop knobs. `max_rounds=None` means run until plateau or stop signal."""

    round_interval_sec: float = 300.0
    max_stale_rounds: int = 3
    max_rounds: int | None = None
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    lookback_days: int = 60


class ImproveUntilPlateau:
    """Run rounds until the metric plateaus, then idle/stop."""

    def __init__(self, step: RoundStep, config: LoopConfig) -> None:
        self._step = step
        self._config = config
        self._best: float | None = None
        self._stale_rounds = 0
        self._round_n = 0
        self._stop = asyncio.Event()

    @property
    def best(self) -> float | None:
        return self._best

    @property
    def rounds(self) -> int:
        return self._round_n

    def request_stop(self) -> None:
        self._stop.set()

    async def run_forever(self, container: Container) -> int:
        """Run rounds; returns the number of rounds executed before stopping."""
        while not self._stop.is_set() and not self._max_rounds_reached():
            metric = await self._run_round(container)
            self._record(metric)
            if self._stale_rounds >= self._config.max_stale_rounds:
                logger.info(
                    "improve_loop_plateau",
                    rounds=self._round_n,
                    best=self._best,
                    stale=self._stale_rounds,
                )
                break
            await self._wait_until_next()
        return self._round_n

    async def _run_round(self, container: Container) -> float:
        self._round_n += 1
        logger.info("improve_round_start", round=self._round_n)
        try:
            metric = await self._step(container, self._config)
        except Exception as exc:  # a failed round must not kill the loop
            logger.warning("improve_round_error", round=self._round_n, error=str(exc))
            metric = self._best if self._best is not None else 0.0
        logger.info("improve_round_done", round=self._round_n, metric=metric)
        return metric

    def _record(self, metric: float) -> None:
        previous = self._best
        if previous is None or metric > previous:
            self._best = metric
            self._stale_rounds = 0
            delta = None if previous is None else metric - previous
            logger.info("improve_promoted", metric=metric, delta=delta)
        else:
            self._stale_rounds += 1
            logger.info(
                "improve_stale",
                metric=metric,
                best=previous,
                stale=self._stale_rounds,
            )

    def _max_rounds_reached(self) -> bool:
        limit = self._config.max_rounds
        return limit is not None and self._round_n >= limit

    async def _wait_until_next(self) -> None:
        with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
            await asyncio.wait_for(self._stop.wait(), timeout=self._config.round_interval_sec)


async def default_step(container: Container, config: LoopConfig) -> float:
    """Default round metric: champion-strategy win rate on a recent window.

    Returns 0.0 when there is no seeded candle data yet (the loop then plateaus
    cleanly instead of spinning). Swap this out for the S5 self-improvement
    candidate/backtest/promote step.
    """
    now = datetime.now(UTC)
    start = now - timedelta(days=config.lookback_days)
    query = cast(CandleQueryService, await container.aresolve(CandleQueryService))
    candles = await query.range(
        Symbol.of(config.symbol), Timeframe(config.timeframe), start, now
    )
    if not candles:
        logger.info("improve_no_data", symbol=config.symbol)
        return 0.0

    manager = cast(StrategyManager, await container.aresolve(StrategyManager))
    champion = next(
        (m.strategy_id for m in manager.list()),
        None,
    )
    if champion is None:
        logger.warning("improve_no_strategy_registered")
        return 0.0

    engine = cast(BacktestEngine, await container.aresolve(BacktestEngine))
    result = await engine.run(
        BacktestConfig(
            symbol=config.symbol,
            timeframe=config.timeframe,
            strategy_id=champion,
            start=start,
            end=now,
        )
    )
    if result.is_err:
        logger.warning("improve_backtest_err", error=result.error_value)
        return 0.0
    score = result.ok_value().win_rate_pct
    return float(score)


async def main() -> int:
    settings = get_settings()
    config = LoopConfig(
        round_interval_sec=settings.self_improve.round_interval_sec,
        max_stale_rounds=settings.self_improve.max_stale_rounds,
        max_rounds=settings.self_improve.max_rounds,
        symbol=settings.self_improve.symbol,
        timeframe=settings.self_improve.timeframe,
        lookback_days=settings.self_improve.lookback_days,
    )
    loop = ImproveUntilPlateau(default_step, config)
    _install_signal_handlers(loop)

    container = build_container(settings)
    await initialize(container)
    logger.info("improve_loop_start", config=vars(config))
    try:
        rounds = await loop.run_forever(container)
        logger.info("improve_loop_stopped", rounds=rounds, best=loop.best)
        return 0
    finally:
        await shutdown(container)


def _install_signal_handlers(loop: ImproveUntilPlateau) -> None:
    running = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError, RuntimeError):
            running.add_signal_handler(sig, loop.request_stop)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))