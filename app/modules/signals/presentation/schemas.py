from pydantic import BaseModel


class FeatureVectorResponse(BaseModel):
    symbol: str
    timeframe: str
    timestamp: str
    features: dict[str, float]
