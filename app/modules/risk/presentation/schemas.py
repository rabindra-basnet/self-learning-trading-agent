from pydantic import BaseModel

from app.modules.risk.domain.entities import RiskDecision, RiskProfile


class RiskProfileResponse(BaseModel):
    profile: RiskProfile


class RiskDecisionResponse(BaseModel):
    decision: RiskDecision


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str | None = None
