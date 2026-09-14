"""strategies http routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.modules.strategies.api.schemas import EvaluateResponse, StrategyMeta
from app.modules.strategies.application.manager import StrategyManager

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _get_manager(request: Request) -> StrategyManager:
    return request.app.state.container  # type: ignore[no-any-return]


@router.get("", response_model=list[StrategyMeta])
def list_strategies(manager: Annotated[StrategyManager, Depends(_get_manager)]) -> list[StrategyMeta]:
    return manager.list()


@router.post("/{strategy_id}/evaluate", response_model=EvaluateResponse)
def evaluate(
    strategy_id: str,
    manager: Annotated[StrategyManager, Depends(_get_manager)],
    symbol: str = "BTC-USDT",
    timeframe: str = "1h",
) -> EvaluateResponse:
    try:
        signal = manager.evaluate(strategy_id, (), ())
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown strategy: {strategy_id}") from None
    return EvaluateResponse(
        strategy_id=strategy_id, symbol=symbol, timeframe=timeframe, signal=signal.value
    )