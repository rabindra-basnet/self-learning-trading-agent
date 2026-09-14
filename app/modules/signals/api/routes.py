"""signals inbound routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request

from app.modules.marketdata.application.services import CandleQueryService
from app.modules.marketdata.domain.entities import Symbol, Timeframe
from app.modules.signals.api.schemas import FeatureVectorResponse
from app.modules.signals.application.services import FeatureService

router = APIRouter(prefix="/signals", tags=["signals"])


def _query(request: Request) -> CandleQueryService:
    return request.app.state.container.resolve(CandleQueryService)


def _features(request: Request) -> FeatureService:
    return request.app.state.container.resolve(FeatureService)


@router.get("/features", response_model=list[FeatureVectorResponse])
async def compute_features(request: Request, symbol: str = "BTC/USDT", timeframe: str = "1h", hours: int = 24):
    candles = await _query(request).range(
        Symbol.of(symbol),
        Timeframe(timeframe),
        datetime.now(UTC) - timedelta(hours=hours),
        datetime.now(UTC),
    )
    vectors = await _features(request).compute(candles)
    return [
        FeatureVectorResponse(
            symbol=v.symbol,
            timeframe=v.timeframe,
            timestamp=v.timestamp.isoformat(),
            features=v.features,
        )
        for v in vectors
    ]
