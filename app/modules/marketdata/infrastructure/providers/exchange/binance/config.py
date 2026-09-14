"""Binance boundary config — owned here, translated from core Settings by the composition root."""

from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class BinanceConfig(BaseModel):
    base_url: str = "https://api.binance.com"
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    api_secret: SecretStr = Field(default_factory=lambda: SecretStr(""))
    rate_per_sec: float = 5.0
    timeout_sec: float = 10.0
    retries: int = 3
    backoff_base_sec: float = 0.5
    circuit_open_after: int = 5
