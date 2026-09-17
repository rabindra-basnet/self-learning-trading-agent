"""marketdata inbound adapter (FastAPI)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi import APIRouter, HTTPException, Request

from app.core.exceptions.taxonomy import http_status_for
from app.modules.marketdata.application.services import CandleIngestService, CandleQueryService
from app.modules.marketdata.domain.entities import Candle, Symbol, Timeframe
from app.modules.marketdata.presentation.schemas import CandleSummary, SyncRequest

router = APIRouter(prefix="/market-data", tags=["market-data"])


def _service(request: Request) -> CandleIngestService:
    return cast("CandleIngestService", request.app.state.container.resolve(CandleIngestService))


def _query(request: Request) -> CandleQueryService:
    return cast("CandleQueryService", request.app.state.container.resolve(CandleQueryService))


@router.post("/sync", response_model=CandleSummary, status_code=201)
async def sync(body: SyncRequest, request: Request) -> CandleSummary:
    tf = Timeframe(body.timeframe)
    result = await _service(request).sync(symbol=Symbol.of(body.symbol), timeframe=tf, limit=body.limit)
    if result.is_err:
        error = result.error_value()
        raise HTTPException(status_code=http_status_for(error), detail=error.message)
    s = result.ok_value()
    return CandleSummary(symbol=s.symbol.code, timeframe=tf.value, appended=s.appended, fetched=s.fetched)


@router.get("/candles")
async def get_candles(
    request: Request,
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    start: str | None = None,
    end: str | None = None,
    limit: int = 100,
) -> list[Candle]:
    tf = Timeframe(timeframe)
    sym = Symbol.of(symbol)
    s = datetime.fromisoformat(start).replace(tzinfo=UTC) if start else datetime.now(UTC) - timedelta(hours=24)
    e = datetime.fromisoformat(end).replace(tzinfo=UTC) if end else datetime.now(UTC)
    return await _query(request).range(sym, tf, s, e)
