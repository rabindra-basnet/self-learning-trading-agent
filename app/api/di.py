"""Composition root — wires real adapters + providers into the container.

Lives in the app layer; everything below depends only on contracts/ports.
All adapters selected here are SKIN, fully replaceable per environment.
"""

from __future__ import annotations

import contextlib

from app.core.common.clock import SystemClock
from app.core.config.settings import Settings
from app.core.container import Container
from app.core.logging.setup import configure_logging
from app.core.messaging.bus import EventBus, InMemoryEventBus
from app.core.messaging.outbox import NoopOutbox, OutboxPublisher
from app.core.observability.metrics import NoopMeter
from app.infrastructure.capability.bus.redis_bus import RedisEventBus
from app.infrastructure.capability.database import (
    ClickHouseConnection,
    PostgresConnection,
)
from app.infrastructure.capability.outbox.redis_outbox import RedisOutbox
from app.infrastructure.capability.redis import RedisConnection
from app.infrastructure.stores.in_memory.candle_store import InMemoryCandleStore
from app.modules.auth.application.services import (
    ApiKeyService,
    AuthService,
)
from app.modules.auth.infrastructure.providers.auth.hashers import (
    Pbkdf2PasswordHasher,
)
from app.modules.auth.infrastructure.providers.auth.jwt.manager import (
    JwtTokenManager,
)
from app.modules.auth.infrastructure.stores.in_memory_repos import (
    InMemoryApiKeyRepository,
    InMemoryUserRepository,
)
from app.modules.backtest.application.engine import BacktestEngine
from app.modules.marketdata.application.services import (
    CandleIngestService,
    CandleQueryService,
)
from app.modules.risk.application.services import RiskService
from app.modules.risk.infrastructure.stores.in_memory import (
    InMemoryRiskProfileStore,
)
from app.modules.signals.application.services import FeatureService
from app.modules.signals.infrastructure.providers.indicators.pandas.adapter import (
    PandasFeatureComputer,
)
from app.modules.strategies.application.manager import StrategyManager
from app.modules.strategies.domain.ports import Strategy
from app.modules.strategies.infrastructure.providers.strategies.library import (
    builtin_strategies,
)


def build_container(settings: Settings) -> Container:
    configure_logging()

    container = Container()
    clock = SystemClock()

    # --- capability connections -----------------------------------------
    pg = PostgresConnection(settings.database.url)
    ch = ClickHouseConnection(
        host=settings.clickhouse.host,
        port=settings.clickhouse.port,
        user=settings.clickhouse.user,
        password=settings.clickhouse.password,
        database=settings.clickhouse.database,
    )
    rd = RedisConnection(settings.redis.url)
    container.register_instance(PostgresConnection, pg)
    container.register_instance(ClickHouseConnection, ch)
    container.register_instance(RedisConnection, rd)

    # --- event bus (in_memory | redis_streams) --------------------------
    if settings.event_bus == "redis_streams":
        bus: EventBus = RedisEventBus(rd.client)
    else:
        bus = InMemoryEventBus()
    container.register_instance(RedisEventBus, RedisEventBus(rd.client))
    container._event_bus = bus  # type: ignore[attr-defined]

    # --- outbox / metrics -----------------------------------------------
    container.register(NoopOutbox, NoopOutbox())
    container.register(RedisOutbox, RedisOutbox(rd.client))
    container.register(NoopMeter, NoopMeter())
    container.register(
        OutboxPublisher,
        lambda: OutboxPublisher(
            outbox=container.resolve(NoopOutbox),
            bus=_bus(container),
            meter=container.resolve(NoopMeter),
        ),
    )

    # --- auth -----------------------------------------------------------
    hasher = Pbkdf2PasswordHasher()
    token = JwtTokenManager(
        secret=settings.auth.jwt_secret.get_secret_value(),
        access_ttl_min=settings.auth.access_ttl_min,
        refresh_ttl_days=settings.auth.refresh_ttl_days,
        algorithm=settings.auth.jwt_alg,
    )
    users = InMemoryUserRepository()
    keys = InMemoryApiKeyRepository()
    container.register_instance(Pbkdf2PasswordHasher, hasher)
    container.register_instance(JwtTokenManager, token)
    container.register_instance(InMemoryUserRepository, users)
    container.register_instance(InMemoryApiKeyRepository, keys)
    container.register(
        AuthService,
        lambda: AuthService(users, hasher, token, clock),
    )
    container.register(
        ApiKeyService,
        lambda: ApiKeyService(keys, users, hasher, clock),
    )

    # --- marketdata -----------------------------------------------------
    store = InMemoryCandleStore()
    container.register_instance(InMemoryCandleStore, store)
    container.register(
        CandleIngestService,
        lambda: CandleIngestService(store, store, _bus(container), clock),
    )
    container.register(
        CandleQueryService,
        lambda: CandleQueryService(store),
    )

    # --- signals --------------------------------------------------------
    computer = PandasFeatureComputer()
    container.register(PandasFeatureComputer, computer)
    container.register(
        FeatureService,
        lambda: FeatureService(computer, _bus(container)),
    )

    # --- strategies -----------------------------------------------------
    strategy_store = _InMemoryStrategyStore()
    manager = StrategyManager(strategy_store, _bus(container))
    container.register_instance(StrategyManager, manager)

    # --- backtest -------------------------------------------------------
    container.register(
        BacktestEngine,
        lambda: BacktestEngine(store, computer, manager, _bus(container)),
    )

    # --- risk -----------------------------------------------------------
    container.register(
        RiskService,
        lambda: RiskService(InMemoryRiskProfileStore(), _bus(container)),
    )

    return container


async def initialize(container: Container) -> None:
    """Async wiring that needs an event loop (strategy registration emits events)."""
    manager = container.resolve(StrategyManager)
    for strategy in builtin_strategies().values():
        await manager.register(strategy)


async def shutdown(container: Container) -> None:
    with contextlib.suppress(Exception):
        await container.resolve(PostgresConnection).dispose()
    with contextlib.suppress(Exception):
        await container.resolve(ClickHouseConnection).dispose()
    with contextlib.suppress(Exception):
        await container.resolve(RedisConnection).dispose()
    bus = getattr(container, "_event_bus", None)
    if bus is not None and hasattr(bus, "close"):
        with contextlib.suppress(Exception):
            await bus.close()


def _bus(container: Container) -> EventBus:
    return container._event_bus  # type: ignore[return-value]


class _InMemoryStrategyStore:
    """Minimal StrategyStore to satisfy StrategyManager."""

    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}

    def register(self, strategy: Strategy) -> None:
        self._strategies[strategy.strategy_id] = strategy

    def get(self, strategy_id: str) -> Strategy | None:
        return self._strategies.get(strategy_id)

    def list_meta(self) -> list:
        from app.modules.strategies.domain.entities import StrategyMeta

        return [
            StrategyMeta(
                strategy_id=sid,
                name=s.params.name,
                params=s.params.model_dump(),
            )
            for sid, s in self._strategies.items()
        ]
