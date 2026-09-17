"""strategies http routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from magic_di.fastapi import Provide

from app.core.exceptions.taxonomy import http_status_for
from app.modules.strategies.application.manager import StrategyManager
from app.modules.strategies.presentation.schemas import EvaluateResponse, StrategyMeta

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", response_model=list[StrategyMeta])
async def list_strategies(
    manager: Provide[StrategyManager],
) -> list[StrategyMeta]:
    return await manager.list()


@router.post("/{strategy_id}/evaluate", response_model=EvaluateResponse)
async def evaluate(
    strategy_id: str,
    manager: Provide[StrategyManager],
    symbol: str = "BTC-USDT",
    timeframe: str = "1h",
) -> EvaluateResponse:
    result = await manager.evaluate(strategy_id, (), ())
    if result.is_err:
        raise HTTPException(status_code=http_status_for(result.error_value()), detail=result.error_value().message)
    return EvaluateResponse(strategy_id=strategy_id, symbol=symbol, timeframe=timeframe, signal=result.ok_value().value)
