"""Yahoo chart response shapes, exactly as the vendor sends them.

Field names mirror the vendor payload; nothing outside this package imports
these models.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class YahooQuoteSeries(BaseModel):
    open: list[float | None] = Field(default_factory=list)
    high: list[float | None] = Field(default_factory=list)
    low: list[float | None] = Field(default_factory=list)
    close: list[float | None] = Field(default_factory=list)
    volume: list[float | None] = Field(default_factory=list)


class YahooIndicators(BaseModel):
    quote: list[YahooQuoteSeries] = Field(default_factory=list)


class YahooMeta(BaseModel):
    symbol: str = ""
    currency: str = ""
    regularMarketPrice: float | None = None
    chartPreviousClose: float | None = None
    regularMarketTime: int | None = None


class YahooChartResult(BaseModel):
    meta: YahooMeta = Field(default_factory=YahooMeta)
    timestamp: list[int] | None = None
    indicators: YahooIndicators = Field(default_factory=YahooIndicators)


class YahooChart(BaseModel):
    result: list[YahooChartResult] | None = None
    error: dict[str, Any] | None = None


class YahooEnvelope(BaseModel):
    chart: YahooChart
