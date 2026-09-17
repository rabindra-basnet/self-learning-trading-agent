"""Yahoo Finance boundary config — owned here (docs/INTEGRATION-ARCHITECTURE.md §5/§6).

No API key: the public chart endpoint is keyless. Reads its own
``MARKET_DATA_YAHOO_*`` environment block.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class YahooConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="MARKET_DATA_YAHOO_",
        extra="ignore",
    )

    base_url: str = "https://query1.finance.yahoo.com"
    user_agent: str = "Mozilla/5.0 (compatible; self-learning-trading-agent/0.1)"
    rate_per_sec: float = 3.0
    timeout_sec: float = 10.0
    retries: int = 3
    backoff_base_sec: float = 0.5
    circuit_open_after: int = 5
