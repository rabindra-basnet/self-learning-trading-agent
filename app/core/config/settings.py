"""Application + integration configuration (pydantic-settings).

Provider-specific config is OWned by each integration boundary. The top-level
`Settings` only selects *which* provider for a capability.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BinanceConfig(BaseModel):
    base_url: str = "https://api.binance.com"
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    api_secret: SecretStr = Field(default_factory=lambda: SecretStr(""))
    rate_per_sec: int = 5
    timeout_sec: float = 10.0
    retries: int = 3
    backoff_base_sec: float = 0.5
    circuit_open_after: int = 5


class MarketDataSettings(BaseModel):
    provider: str = "binance"  # swap knob: binance | kraken | ...
    binance: BinanceConfig = Field(default_factory=BinanceConfig)


class LlmSettings(BaseModel):
    provider: str = "zen"
    base_url: str = "https://opencode.ai/zen/v1"
    model: str = "nemotron-3-ultra-free"
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    timeout_sec: float = 60.0
    retries: int = 3


class DatabaseSettings(BaseModel):
    url: str = "postgresql+asyncpg://trading:trading@localhost:5432/trading"


class ClickHouseSettings(BaseModel):
    host: str = "localhost"
    port: int = 8123
    user: str = "default"
    password: str = ""
    database: str = "trading"


class RedisSettings(BaseModel):
    url: str = "redis://localhost:6379/0"


class AuthSettings(BaseModel):
    jwt_secret: SecretStr
    jwt_alg: str = "HS256"
    access_ttl_min: int = 15
    refresh_ttl_days: int = 7


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_env: str = "dev"
    log_level: str = "INFO"

    auth: AuthSettings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    clickhouse: ClickHouseSettings = Field(default_factory=ClickHouseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)

    market_data: MarketDataSettings = Field(default_factory=MarketDataSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)

    event_bus: str = "in_memory"  # in_memory | redis_streams


@lru_cache
def get_settings() -> Settings:
    return Settings()
