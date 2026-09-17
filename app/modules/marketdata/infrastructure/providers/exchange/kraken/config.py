"""Kraken boundary config — owned here (docs/INTEGRATION-ARCHITECTURE.md §5/§6).

Public OHLC/Ticker endpoints need no key, so credentials stay optional and are
only used if private endpoints are added later.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class KrakenConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="MARKET_DATA_KRAKEN_",
        extra="ignore",
    )

    base_url: str = "https://api.kraken.com"
    user_agent: str = "self-learning-trading-agent/0.1"
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    api_secret: SecretStr = Field(default_factory=lambda: SecretStr(""))
    rate_per_sec: float = 3.0
    timeout_sec: float = 10.0
    retries: int = 3
    backoff_base_sec: float = 0.5
    circuit_open_after: int = 5
