"""risk inbound routes."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Request

from app.modules.risk.api.schemas import (
    KillSwitchRequest,
    RiskDecisionResponse,
    RiskProfileResponse,
)
from app.modules.risk.application.services import RiskService
from app.modules.risk.domain.entities import KillSwitchState

router = APIRouter(prefix="/risk", tags=["risk"])


def _service(request: Request) -> RiskService:
    return request.app.state.container.resolve(RiskService)


@router.get("/profile", response_model=RiskProfileResponse)
async def get_profile(request: Request) -> RiskProfileResponse:
    return RiskProfileResponse(profile=await _service(request).get_profile())


@router.put("/profile", response_model=RiskProfileResponse)
async def set_profile(request: Request, profile: RiskProfileResponse) -> RiskProfileResponse:
    saved = await _service(request).set_profile(profile.profile)
    return RiskProfileResponse(profile=saved)


@router.post("/check")
async def check_order(request: Request, symbol: str = "BTC/USDT", notional: str = "0", equity: str = "10000"):
    decision = await _service(request).check_order(
        symbol=symbol,
        notional=Decimal(notional),
        equity=Decimal(equity),
        daily_loss=Decimal("0.001"),
        position_pct=Decimal(notional) / Decimal(equity) if Decimal(equity) else Decimal("0"),
    )
    return RiskDecisionResponse(decision=decision)


@router.put("/kill-switch", response_model=KillSwitchState)
async def set_kill_switch(request: Request, body: KillSwitchRequest) -> KillSwitchState:
    return await _service(request).kill_switch(body.active, body.reason)
