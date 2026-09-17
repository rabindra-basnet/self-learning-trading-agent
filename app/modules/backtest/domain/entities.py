"""backtest domain: config, trades, results — deterministic and seed-locked."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.messaging.bus import DomainEvent


class BacktestConfig(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    strategy_id: str
    start: datetime = Field(description="inclusive start")
    end: datetime = Field(description="inclusive end")
    initial_capital: Decimal = Decimal("10000")
    fee_pct: Decimal = Decimal("0.001")
    seed: int | None = None


class BacktestTrade(BaseModel):
    symbol: str
    opened_at: datetime
    closed_at: datetime | None = None
    side: str
    entry: Decimal
    exit: Decimal | None = None
    quantity: Decimal
    pnl: Decimal | None = None


class BacktestResult(BaseModel):
    config: BacktestConfig
    trades: list[BacktestTrade]
    initial_capital: Decimal
    final_capital: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    win_rate_pct: Decimal
    trade_count: int
    extended_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BacktestCompleted(DomainEvent):
    symbol: str
    strategy_id: str
    trade_count: int
    total_return_pct: str
