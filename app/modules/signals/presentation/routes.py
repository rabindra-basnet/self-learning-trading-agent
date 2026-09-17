"""signals inbound routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi import APIRouter, Request

from app.modules.marketdata.contracts import Symbol, Timeframe
from app.modules.signals.application.services import FeatureService
from app.modules.signals.contracts import CandleQueryPort
from app.modules.signals.presentation.schemas import FeatureVectorResponse

router = APIRouter(prefix="/signals", tags=["signals"])


def _query(request: Request) -> CandleQueryPort:
    return cast("CandleQueryPort", request.app.state.container.resolve(CandleQueryPort))


def _features(request: Request) -> FeatureService:
    return cast("FeatureService", request.app.state.container.resolve(FeatureService))


@router.get("/features", response_model=list[FeatureVectorResponse])
async def compute_features(
    request: Request, symbol: str = "BTC/USDT", timeframe: str = "1h", hours: int = 24
) -> list[FeatureVectorResponse]:
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
