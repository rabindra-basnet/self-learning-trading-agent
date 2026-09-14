"""risk domain ports."""

from __future__ import annotations

from typing import Protocol

from app.modules.risk.domain.entities import KillSwitchState, RiskProfile


class RiskProfileStore(Protocol):
    async def get_profile(self) -> RiskProfile: ...

    async def save_profile(self, profile: RiskProfile) -> None: ...

    async def get_kill_switch(self) -> KillSwitchState: ...

    async def set_kill_switch(self, state: KillSwitchState) -> None: ...
