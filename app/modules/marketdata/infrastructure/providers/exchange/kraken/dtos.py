"""Kraken response envelope as the vendor sends it."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KrakenResponse(BaseModel):
    error: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
