from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FeatureVector(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    features: dict[str, float]
