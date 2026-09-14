from pydantic import BaseModel


class StrategyMetaResponse(BaseModel):
    strategy_id: str
    name: str
    params: dict


class EvaluateResponse(BaseModel):
    strategy_id: str
    signal: str
