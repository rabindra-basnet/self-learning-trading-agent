"""marketdata inbound adapter (FastAPI)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from magic_di.fastapi import Provide

from app.core.exceptions.taxonomy import http_status_for
from app.modules.marketdata.application.services import CandleIngestService, CandleQueryService
from app.modules.marketdata.domain.entities import Candle, Symbol, Timeframe
from app.modules.marketdata.presentation.schemas import CandleSummary, SyncRequest

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.post("/sync", response_model=CandleSummary, status_code=201)
async def sync(body: SyncRequest, service: Provide[CandleIngestService]) -> CandleSummary:
    tf = Timeframe(body.timeframe)
    result = await service.sync(symbol=Symbol.of(body.symbol), timeframe=tf, limit=body.limit)
    if result.is_err:
        error = result.error_value()
        raise HTTPException(status_code=http_status_for(error), detail=error.message)
    s = result.ok_value()
    return CandleSummary(symbol=s.symbol.code, timeframe=tf.value, appended=s.appended, fetched=s.fetched)


@router.get("/candles")
async def get_candles(
    query_service: Provide[CandleQueryService],
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
    return await query_service.range(sym, tf, s, e)
