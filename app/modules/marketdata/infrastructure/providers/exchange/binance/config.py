"""Binance boundary config — owned here (docs/INTEGRATION-ARCHITECTURE.md §5/§6).

Reads its own ``MARKET_DATA_BINANCE_*`` environment block so the vendor boundary
stays self-contained: adding another exchange means adding another vendor package,
not editing `app/core/config/settings.py`.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BinanceConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="MARKET_DATA_BINANCE_",
        extra="ignore",
    )

    base_url: str = "https://api.binance.com"
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    api_secret: SecretStr = Field(default_factory=lambda: SecretStr(""))
    rate_per_sec: float = 5.0
    timeout_sec: float = 10.0
    retries: int = 3
    backoff_base_sec: float = 0.5
    circuit_open_after: int = 5
