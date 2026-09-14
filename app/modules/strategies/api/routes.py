"""strategies inbound routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.common.result import Err
from app.core.exceptions.taxonomy import http_status_for
from app.modules.strategies.api.schemas import EvaluateResponse, StrategyMetaResponse
from app.modules.strategies.application.manager import StrategyManager

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _manager(request: Request) -> StrategyManager:
    return request.app.state.container.resolve(StrategyManager)


@router.get("", response_model=list[StrategyMetaResponse])
async def list_strategies(request: Request) -> list[StrategyMetaResponse]:
    return [StrategyMetaResponse(**meta.model_dump()) for meta in _manager(request).list()]


@router.post("/{strategy_id}/evaluate", response_model=EvaluateResponse)
async def evaluate(
    request: Request,
    strategy_id: str,
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    limit: int = 200,
):
    result = await _evaluate_endpoint(request, strategy_id, symbol, timeframe, limit)
    if isinstance(result, Err):
        raise HTTPException(status_code=http_status_for(result.error_value), detail=result.error_value.message)
    return EvaluateResponse(strategy_id=strategy_id, signal=result.ok_value())


async def _evaluate_endpoint(request: Request, strategy_id: str, symbol: str, timeframe: str, limit: int):
    from datetime import UTC, datetime, timedelta

    from app.modules.marketdata.application.services import CandleQueryService
    from app.modules.marketdata.domain.entities import Symbol, Timeframe
    from app.modules.signals.application.services import FeatureService

    query = request.app.state.container.resolve(CandleQueryService)
    computer = request.app.state.container.resolve(FeatureService)
    candles = await query.range(
        Symbol.of(symbol),
        Timeframe(timeframe),
        datetime.now(UTC) - timedelta(hours=24 * 7),
        datetime.now(UTC),
    )
    if len(candles) > limit:
        candles = candles[-limit:]
    return _manager(request).evaluate(strategy_id, candles, await computer.compute(candles))
