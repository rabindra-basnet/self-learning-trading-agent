"""Twelve Data boundary config — owned here (docs/INTEGRATION-ARCHITECTURE.md §5/§6).

The API key is REQUIRED and has no default: selecting this provider without a
key fails at construction (fail-closed) instead of issuing anonymous calls.
"""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TwelveDataConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="MARKET_DATA_TWELVEDATA_",
        extra="ignore",
    )

    api_key: SecretStr
    base_url: str = "https://api.twelvedata.com"
    rate_per_sec: float = 1.0  # free tier: 8 credits/min
    timeout_sec: float = 15.0
    retries: int = 3
    backoff_base_sec: float = 1.0
    circuit_open_after: int = 4
