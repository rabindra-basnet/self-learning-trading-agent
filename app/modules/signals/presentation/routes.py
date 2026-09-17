"""signals inbound routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from magic_di.fastapi import Provide

from app.modules.marketdata.contracts import Symbol, Timeframe
from app.modules.signals.application.services import FeatureService
from app.modules.signals.contracts import CandleQueryPort
from app.modules.signals.presentation.schemas import FeatureVectorResponse

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/features", response_model=list[FeatureVectorResponse])
async def compute_features(
    query_port: Provide[CandleQueryPort],
    features_svc: Provide[FeatureService],
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    hours: int = 24,
) -> list[FeatureVectorResponse]:
    candles = await query_port.range(
        Symbol.of(symbol),
        Timeframe(timeframe),
        datetime.now(UTC) - timedelta(hours=hours),
        datetime.now(UTC),
    )
    vectors = await features_svc.compute(candles)
    return [
        FeatureVectorResponse(
            symbol=v.symbol,
            timeframe=v.timeframe,
            timestamp=v.timestamp.isoformat(),
            features=v.features,
        )
        for v in vectors
    ]
