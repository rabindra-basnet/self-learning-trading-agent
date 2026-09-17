"""Composition root — wires real adapters + providers into the container.

Lives in the app layer; everything below depends only on contracts/ports.
All adapters selected here are SKIN, fully replaceable per environment.
Real adapters only: Postgres (auth), ClickHouse (candles), Redis (bus/outbox),
Binance (market data).
"""

from __future__ import annotations

import asyncio
from typing import cast

from app.core.common.clock import SystemClock
from app.core.config.settings import Settings
from app.core.container import Container
from app.core.exceptions.taxonomy import ConfigurationError, FatalSystemError
from app.core.logging.setup import configure_logging
from app.core.messaging.bus import EventBus
from app.core.messaging.outbox import Outbox, OutboxPublisher
from app.core.observability.metrics import NoopMeter
from app.infrastructure.capability.bus.redis_bus import RedisEventBus
from app.infrastructure.capability.database import ClickHouseConnection, PostgresConnection
from app.infrastructure.capability.outbox.redis_outbox import RedisOutbox
from app.infrastructure.capability.redis import RedisConnection
from app.infrastructure.providers.registry import UnknownProviderError, provider_registry
from app.infrastructure.stores.clickhouse.candle_store import ClickHouseCandleStore
from app.modules.auth.application.services import ApiKeyService, AuthService
from app.modules.auth.domain.ports import ApiKeyRepository, UserRepository
from app.modules.auth.infrastructure.providers.auth.hashers import Pbkdf2PasswordHasher
from app.modules.auth.infrastructure.providers.auth.jwt.manager import JwtTokenManager
from app.modules.auth.infrastructure.stores import (
    PostgresApiKeyRepository,
    PostgresUserRepository,
)
from app.modules.backtest.application.engine import BacktestEngine
from app.modules.marketdata.application.services import CandleIngestService, CandleQueryService
from app.modules.marketdata.domain.ports import CandleStore, MarketDataSource
from app.modules.marketdata.infrastructure.providers.registry import (
    CAPABILITY as MARKET_DATA_CAPABILITY,
)
from app.modules.marketdata.infrastructure.providers.registry import (
    register_market_data_providers,
)
from app.modules.risk.application.services import RiskService
from app.modules.risk.infrastructure.stores import RedisRiskProfileStore
from app.modules.signals.application.services import FeatureService
from app.modules.signals.contracts import CandleQueryPort
from app.modules.signals.infrastructure.providers.indicators.pandas.adapter import (
    PandasFeatureComputer,
)
from app.modules.strategies.application.manager import StrategyManager
from app.modules.strategies.infrastructure.providers.strategies.library import (
    BUILTIN_STRATEGIES,
)
from app.modules.strategies.infrastructure.stores import StrategyLibraryStore


def build_container(settings: Settings) -> Container:
    configure_logging(env=settings.app_env, level=settings.log_level)

    container = Container()
    clock = SystemClock()

    # --- capability connections -----------------------------------------
    pg = PostgresConnection(settings.database_url)
    ch = ClickHouseConnection(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
        secure=settings.clickhouse_secure,
    )
    rd = RedisConnection(settings.redis_url)
    container.register_instance(PostgresConnection, pg)
    container.register_instance(ClickHouseConnection, ch)
    container.register_instance(RedisConnection, rd)

    # --- event bus (Redis Streams, durable) -----------------------------
    bus = RedisEventBus(rd.client)
    container.register_instance(EventBus, bus)
    container.register_instance(RedisEventBus, bus)

    # --- outbox / metrics ------------------------------------------------
    outbox = RedisOutbox(rd.client)
    meter = NoopMeter()
    container.register_instance(Outbox, outbox)
    container.register_instance(NoopMeter, meter)
    container.register(
        OutboxPublisher,
        lambda: OutboxPublisher(outbox=outbox, bus=bus, meter=meter),
    )

    # --- auth (Postgres identity store) ----------------------------------
    hasher = Pbkdf2PasswordHasher()
    token = JwtTokenManager(
        secret=settings.auth_jwt_secret.get_secret_value(),
        access_ttl_min=settings.auth_access_ttl_min,
        refresh_ttl_days=settings.auth_refresh_ttl_days,
        algorithm=settings.auth_jwt_alg,
    )
    users = PostgresUserRepository(pg.session_factory)
    keys = PostgresApiKeyRepository(pg.session_factory)
    container.register_instance(Pbkdf2PasswordHasher, hasher)
    container.register_instance(JwtTokenManager, token)
    container.register_instance(UserRepository, users)
    container.register_instance(ApiKeyRepository, keys)
    container.register(AuthService, lambda: AuthService(users, hasher, token, clock))
    container.register(ApiKeyService, lambda: ApiKeyService(keys, users, hasher, clock))

    # --- marketdata (Binance → ClickHouse) --------------------------------
    candle_store = ClickHouseCandleStore(ch)
    market_data = _build_market_data(settings)
    query_service = CandleQueryService(candle_store)
    container.register_instance(CandleStore, candle_store)
    container.register_instance(MarketDataSource, market_data)
    container.register_instance(CandleQueryService, query_service)
    container.register_instance(CandleQueryPort, query_service)
    container.register(
        CandleIngestService,
        lambda: CandleIngestService(market_data, candle_store, bus, clock),
    )

    # --- signals ----------------------------------------------------------
    computer = PandasFeatureComputer()
    container.register_instance(PandasFeatureComputer, computer)
    container.register(FeatureService, lambda: FeatureService(computer, bus))

    # --- strategies -------------------------------------------------------
    manager = StrategyManager(StrategyLibraryStore(BUILTIN_STRATEGIES), bus)
    container.register_instance(StrategyManager, manager)

    # --- backtest ---------------------------------------------------------
    container.register(
        BacktestEngine,
        lambda: BacktestEngine(candle_store, computer, manager, bus),
    )

    # --- risk (Redis-backed profile + kill switch) ------------------------
    container.register(
        RiskService,
        lambda: RiskService(RedisRiskProfileStore(rd.client), bus),
    )

    return container


async def verify_dependencies(container: Container) -> None:
    """Fail-closed gate: abort startup when an external dependency is unreachable."""
    checks = await asyncio.gather(
        container.resolve(PostgresConnection).ping(),
        container.resolve(ClickHouseConnection).ping(),
        container.resolve(RedisConnection).ping(),
    )
    failed = [name for name, ok in zip(("postgres", "clickhouse", "redis"), checks, strict=True) if not ok]
    if failed:
        raise FatalSystemError(f"startup dependency check failed: {', '.join(failed)}")


async def initialize(container: Container) -> None:
    """Async wiring that needs an event loop (strategy registration emits events)."""
    await container.connect()
    await verify_dependencies(container)
    manager = container.resolve(StrategyManager)
    for strategy in BUILTIN_STRATEGIES.values():
        await manager.register(strategy)


async def shutdown(container: Container) -> None:
    """Delegate lifecycle teardown to the injector (dispose/close per adapter)."""
    await container.disconnect()


def _build_market_data(settings: Settings) -> MarketDataSource:
    """Resolve the configured market-data vendor through the provider registry."""
    register_market_data_providers()
    provider = settings.market_data_provider
    try:
        return cast(MarketDataSource, provider_registry.create(MARKET_DATA_CAPABILITY, provider))
    except UnknownProviderError as exc:
        raise ConfigurationError(str(exc), provider=provider) from exc
