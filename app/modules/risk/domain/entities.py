"""risk domain: settings, decisions, events — pure."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.core.messaging.bus import DomainEvent


class RiskProfile(BaseModel):
    max_position_pct: Decimal = Decimal("0.10")
    max_daily_loss_pct: Decimal = Decimal("0.02")
    max_drawdown_pct: Decimal = Decimal("0.15")
    allow_leverage: bool = False
    failed_closed: bool = True


class RiskDecision(BaseModel):
    approved: bool
    reason: str


class KillSwitchState(BaseModel):
    active: bool = False
    reason: str | None = None


class RiskBreached(DomainEvent):
    symbol: str
    reason: str


class KillSwitchTriggered(DomainEvent):
    reason: str
