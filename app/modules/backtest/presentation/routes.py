"""backtest inbound routes."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request

from app.core.common.result import Err
from app.core.exceptions.taxonomy import http_status_for
from app.modules.backtest.presentation.schemas import BacktestRunRequest, BacktestRunResponse
from app.modules.backtest.application.engine import BacktestEngine
from app.modules.backtest.domain.entities import BacktestConfig

router = APIRouter(prefix="/backtest", tags=["backtest"])


def _engine(request: Request) -> BacktestEngine:
    return request.app.state.container.resolve(BacktestEngine)


@router.post("/run", response_model=BacktestRunResponse)
async def run_backtest(request: Request, body: BacktestRunRequest) -> BacktestRunResponse:
    engine = _engine(request)
    config = BacktestConfig(
        symbol=body.symbol,
        timeframe=body.timeframe,
        strategy_id=body.strategy_id,
        start=datetime.fromisoformat(body.start).replace(tzinfo=UTC),
        end=datetime.fromisoformat(body.end).replace(tzinfo=UTC),
        initial_capital=Decimal(body.initial_capital),
        fee_pct=Decimal(body.fee_pct),
        seed=body.seed,
    )
    if body.folds:
        results = await engine.walk_forward(config, body.folds)
        return BacktestRunResponse(results=results)

    result = await engine.run(config)
    if isinstance(result, Err):
        raise HTTPException(status_code=http_status_for(result.error_value), detail=result.error_value.message)
    return BacktestRunResponse(results=[result.ok_value()])
