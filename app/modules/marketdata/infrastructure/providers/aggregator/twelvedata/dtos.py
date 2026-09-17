"""Twelve Data response shapes, exactly as the vendor sends them."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TwelveValue(BaseModel):
    datetime: str
    open: str
    high: str
    low: str
    close: str
    volume: str | None = None


class TwelveTimeSeries(BaseModel):
    meta: dict[str, Any] = Field(default_factory=dict)
    values: list[TwelveValue] = Field(default_factory=list)
    status: str = "ok"
    code: int | None = None
    message: str | None = None


class TwelveQuote(BaseModel):
    symbol: str = ""
    name: str = ""
    close: str = ""
    previous_close: str | None = None
    volume: str | None = None
    timestamp: int | None = None
