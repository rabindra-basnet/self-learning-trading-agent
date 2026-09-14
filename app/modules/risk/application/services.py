"""risk application service — pure risk gates (fail-closed)."""

from __future__ import annotations

from decimal import Decimal

from app.core.messaging.bus import EventBus
from app.modules.risk.domain.entities import (
    KillSwitchState,
    KillSwitchTriggered,
    RiskBreached,
    RiskDecision,
    RiskProfile,
)
from app.modules.risk.domain.ports import RiskProfileStore


class RiskService:
    def __init__(self, store: RiskProfileStore, bus: EventBus) -> None:
        self._store = store
        self._bus = bus

    async def get_profile(self) -> RiskProfile:
        return await self._store.get_profile()

    async def set_profile(self, profile: RiskProfile) -> RiskProfile:
        await self._store.save_profile(profile)
        return profile

    async def check_order(
        self,
        symbol: str,
        notional: Decimal,
        equity: Decimal,
        daily_loss: Decimal,
        position_pct: Decimal,
    ) -> RiskDecision:
        state = await self._store.get_kill_switch()
        if state.active:
            return RiskDecision(approved=False, reason=f"kill_switch: {state.reason or 'active'}")

        profile = await self._store.get_profile()
        if not profile.allow_leverage and position_pct > 1:
            return RiskDecision(approved=False, reason="leverage_disabled")

        if position_pct > profile.max_position_pct:
            return RiskDecision(approved=False, reason="max_position_exceeded")
        if daily_loss > profile.max_daily_loss_pct:
            return RiskDecision(approved=False, reason="daily_loss_exceeded")
        if await self._breach_notify(symbol, position_pct, daily_loss, profile):
            return RiskDecision(approved=False, reason="posture_breach")
        return RiskDecision(approved=True, reason="ok")

    async def kill_switch(self, active: bool, reason: str | None = None) -> KillSwitchState:
        state = KillSwitchState(active=active, reason=reason)
        await self._store.set_kill_switch(state)
        if active:
            await self._bus.publish(KillSwitchTriggered(reason=reason or "manual"))
        return state

    async def _breach_notify(
        self, symbol: str, position_pct: Decimal, daily_loss: Decimal, profile: RiskProfile
    ) -> bool:
        if position_pct > profile.max_position_pct * Decimal(
            "1.5"
        ) or daily_loss > profile.max_daily_loss_pct * Decimal("1.5"):
            await self._bus.publish(RiskBreached(symbol=symbol, reason="posture_breach"))
            return not profile.failed_closed
        return False
