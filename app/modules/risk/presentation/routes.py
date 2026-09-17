"""risk inbound routes."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter
from magic_di.fastapi import Provide

from app.modules.risk.application.services import RiskService
from app.modules.risk.domain.entities import KillSwitchState
from app.modules.risk.presentation.schemas import (
    KillSwitchRequest,
    RiskDecisionResponse,
    RiskProfileResponse,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/profile", response_model=RiskProfileResponse)
async def get_profile(service: Provide[RiskService]) -> RiskProfileResponse:
    return RiskProfileResponse(profile=await service.get_profile())


@router.put("/profile", response_model=RiskProfileResponse)
async def set_profile(profile: RiskProfileResponse, service: Provide[RiskService]) -> RiskProfileResponse:
    saved = await service.set_profile(profile.profile)
    return RiskProfileResponse(profile=saved)


@router.post("/check")
async def check_order(
    service: Provide[RiskService], symbol: str = "BTC/USDT", notional: str = "0", equity: str = "10000"
) -> RiskDecisionResponse:
    decision = await service.check_order(
        symbol=symbol,
        notional=Decimal(notional),
        equity=Decimal(equity),
        daily_loss=Decimal("0.001"),
        position_pct=Decimal(notional) / Decimal(equity) if Decimal(equity) else Decimal("0"),
    )
    return RiskDecisionResponse(decision=decision)


@router.put("/kill-switch", response_model=KillSwitchState)
async def set_kill_switch(body: KillSwitchRequest, service: Provide[RiskService]) -> KillSwitchState:
    return await service.kill_switch(body.active, body.reason)
