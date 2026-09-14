"""backtest application engine — pure, seeded, walk-forward capable."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from app.core.common.result import Err, Ok, Result
from app.core.exceptions.taxonomy import DomainError, InsufficientDataError, NotFoundError
from app.core.messaging.bus import EventBus
from app.modules.backtest.domain.entities import (
    BacktestCompleted,
    BacktestConfig,
    BacktestResult,
    BacktestTrade,
)
from app.modules.backtest.domain.ports import BacktestDataStore, BacktestFeatureComputer
from app.modules.marketdata.contracts import Candle, Symbol, Timeframe
from app.modules.strategies.application.manager import StrategyManager
from app.modules.strategies.domain.ports import SignalDirection


class BacktestEngine:
    def __init__(
        self,
        store: BacktestDataStore,
        computer: BacktestFeatureComputer,
        manager: StrategyManager,
        bus: EventBus,
    ) -> None:
        self._store = store
        self._computer = computer
        self._manager = manager
        self._bus = bus

    def _require_strategy(self, strategy_id: str):
        strategy = self._manager.get_strategy(strategy_id)
        if strategy is None:
            raise NotFoundError(f"unknown strategy: {strategy_id}")
        return strategy

    async def run(self, config: BacktestConfig) -> Result[BacktestResult, DomainError]:
        self._require_strategy(config.strategy_id)
        candles = await self._store.query_range(
            Symbol.of(config.symbol), Timeframe(config.timeframe), config.start, config.end
        )
        if len(candles) < 30:
            return Err(InsufficientDataError("not enough candles for backtest"))
        features = self._computer.compute(candles)
        result = self._simulate(config, candles, features)
        self._bus.publish(
            BacktestCompleted(
                symbol=config.symbol,
                strategy_id=config.strategy_id,
                trade_count=result.trade_count,
                total_return_pct=str(result.total_return_pct),
            )
        )
        return Ok(result)

    def _simulate(self, config: BacktestConfig, candles: list[Candle], feats: list) -> BacktestResult:
        position: SignalDirection | None = None
        entry_at = candles[0].opened_at
        entry_price = Decimal("0")
        capital = config.initial_capital
        quantity = Decimal("0")
        trades: list[BacktestTrade] = []
        peak = capital
        max_dd = Decimal("0")

        for i in range(len(candles)):
            candle = candles[i]
            direction = self._direction(config, candles[: i + 1], feats[: i + 1])

            if position is None and direction == SignalDirection.BUY:
                position = SignalDirection.BUY
                entry_at = candle.opened_at
                entry_price = candle.close
                quantity = capital / entry_price
                capital = Decimal("0")
            elif position == SignalDirection.BUY and direction == SignalDirection.SELL:
                exit_price = candle.close
                gross = quantity * exit_price * (1 - config.fee_pct)
                pnl = (exit_price - entry_price) * quantity - entry_price * quantity * config.fee_pct
                trades.append(
                    BacktestTrade(
                        symbol=config.symbol,
                        opened_at=entry_at,
                        closed_at=candle.opened_at,
                        side="long",
                        entry=entry_price,
                        exit=exit_price,
                        quantity=quantity,
                        pnl=pnl,
                    )
                )
                capital = gross
                quantity = Decimal("0")
                position = None

            mark = capital + quantity * candle.close if position == SignalDirection.BUY else capital
            peak = max(peak, mark)
            if peak > 0:
                max_dd = max(max_dd, (peak - mark) / peak * 100)

        final_price = candles[-1].close
        if position == SignalDirection.BUY:
            gross = quantity * final_price * (1 - config.fee_pct)
            pnl = (final_price - entry_price) * quantity - entry_price * quantity * config.fee_pct
            trades.append(
                BacktestTrade(
                    symbol=config.symbol,
                    opened_at=entry_at,
                    closed_at=candles[-1].opened_at,
                    side="long",
                    entry=entry_price,
                    exit=final_price,
                    quantity=quantity,
                    pnl=pnl,
                )
            )
            capital = gross

        final_capital = capital + quantity * final_price if position == SignalDirection.BUY else capital
        base = config.initial_capital or Decimal("1")
        total_return = (final_capital - config.initial_capital) / base * 100
        wins = [t for t in trades if t.pnl is not None and t.pnl > 0]
        win_rate = Decimal(len(wins)) / Decimal(len(trades)) * 100 if trades else Decimal("0")
        return BacktestResult(
            config=config,
            trades=trades,
            initial_capital=config.initial_capital,
            final_capital=final_capital,
            total_return_pct=total_return,
            max_drawdown_pct=max_dd,
            win_rate_pct=win_rate,
            trade_count=len(trades),
        )

    def _direction(self, config: BacktestConfig, candles: list[Candle], feats: list):
        result = self._manager.evaluate(config.strategy_id, candles, feats)
        if isinstance(result, Err):
            raise result.error_value
        signal = result.ok_value()
        return SignalDirection(signal) if signal in ("BUY", "SELL", "HOLD") else SignalDirection.HOLD

    async def walk_forward(self, config: BacktestConfig, folds: int = 4) -> list[BacktestResult]:
        results: list[BacktestResult] = []
        total = (config.end - config.start).total_seconds()
        step = total / folds
        for fold in range(folds):
            f_start = config.start + timedelta(seconds=step * fold)
            f_end = f_start + timedelta(seconds=step)
            cfg = config.model_copy(update={"start": f_start, "end": f_end, "seed": (config.seed or 0) + fold})
            res = await self.run(cfg)
            if isinstance(res, Ok):
                results.append(res.ok_value())
        return results
