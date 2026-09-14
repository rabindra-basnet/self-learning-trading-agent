"""In-memory RiskProfileStore adapter."""

from __future__ import annotations

from app.modules.risk.domain.entities import KillSwitchState, RiskProfile


class InMemoryRiskProfileStore:
    def __init__(self) -> None:
        self._profile = RiskProfile()
        self._kill_switch = KillSwitchState()

    async def get_profile(self) -> RiskProfile:
        return self._profile

    async def save_profile(self, profile: RiskProfile) -> None:
        self._profile = profile

    async def get_kill_switch(self) -> KillSwitchState:
        return self._kill_switch

    async def set_kill_switch(self, state: KillSwitchState) -> None:
        self._kill_switch = state
