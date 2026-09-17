"""Application + integration configuration (pydantic-settings).

ONE flat `Settings` class — no nested config models, no delimiter. Env keys are
single-underscore and match the field name exactly (``AUTH_JWT_SECRET``,
``DATABASE_URL``, ``CLICKHOUSE_HOST``, ``MARKET_DATA_BINANCE_API_KEY``, ...).

External-dependency fields (auth secret, Postgres, ClickHouse, Redis) are
REQUIRED and have no defaults, so a missing value raises at construction time
and aborts startup (fail-closed) instead of running half-wired.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # --- runtime ----------------------------------------------------------
    app_env: str = "dev"
    log_level: str = "INFO"
    event_bus: str = "redis_streams"  # redis_streams | (kafka/rabbitmq adapters later)

    # --- required external dependencies (no default -> missing kills startup)
    auth_jwt_secret: SecretStr
    database_url: str
    clickhouse_host: str
    clickhouse_database: str
    redis_url: str

    # --- auth (tunables) --------------------------------------------------
    auth_jwt_alg: str = "HS256"
    auth_access_ttl_min: int = 15
    auth_refresh_ttl_days: int = 7

    # --- clickhouse (tunables) --------------------------------------------
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_secure: bool = False

    # --- market data ------------------------------------------------------
    # The provider name is the ONLY knob (docs/INTEGRATION-ARCHITECTURE.md §6);
    # each vendor owns its own env block (e.g. BinanceConfig reads
    # MARKET_DATA_BINANCE_*) and is picked up via the provider registry.
    market_data_provider: str = "binance"  # binance | kraken | coinbase | ...

    # --- llm --------------------------------------------------------------
    llm_provider: str = "zen"
    llm_base_url: str = "https://opencode.ai/zen/v1"
    llm_model: str = "nemotron-3-ultra-free"
    llm_api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    llm_timeout_sec: float = 60.0
    llm_retries: int = 3

    # --- self-improvement loop --------------------------------------------
    self_improve_enabled: bool = False
    self_improve_round_interval_sec: float = 300.0
    self_improve_max_stale_rounds: int = 3
    self_improve_max_rounds: int | None = None
    self_improve_symbol: str = "BTC/USDT"
    self_improve_timeframe: str = "1h"
    self_improve_lookback_days: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
