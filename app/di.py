"""Composition root — binds ports to adapters via magic-di."""

from __future__ import annotations

from magic_di import DependencyInjector

from app.core.common.clock import Clock, SystemClock
from app.core.config.settings import Settings
from app.core.messaging.bus import EventBus
from app.core.messaging.outbox import Outbox
from app.core.observability.metrics import Meter, NoopMeter
from app.infrastructure.capability.bus.redis_bus import RedisEventBus
from app.infrastructure.capability.outbox.redis_outbox import RedisOutbox
from app.infrastructure.stores.clickhouse.candle_store import ClickHouseCandleStore
from app.modules.auth.domain.ports import (
    ApiKeyRepository,
    PasswordHasher,
    TokenManager,
    UserRepository,
)
from app.modules.auth.infrastructure.providers.auth.hashers import Pbkdf2PasswordHasher
from app.modules.auth.infrastructure.providers.auth.jwt.manager import JwtTokenManager
from app.modules.auth.infrastructure.stores.postgres_repos import PostgresApiKeyRepository, PostgresUserRepository
from app.modules.backtest.domain.ports import (
    BacktestDataStore,
    BacktestFeatureComputer,
    StrategyGateway,
)
from app.modules.marketdata.application.services import CandleQueryService
from app.modules.marketdata.domain.ports import CandleStore, MarketDataSource
from app.modules.marketdata.infrastructure.providers.registry import MarketDataSourceFactory
from app.modules.risk.domain.ports import RiskProfileStore
from app.modules.risk.infrastructure.stores.redis_store import RedisRiskProfileStore
from app.modules.signals.contracts import CandleQueryPort
from app.modules.signals.domain.ports import FeatureComputer
from app.modules.signals.infrastructure.providers.indicators.pandas.adapter import PandasFeatureComputer
from app.modules.strategies.application.manager import StrategyManager
from app.modules.strategies.domain.ports import StrategyStore
from app.modules.strategies.infrastructure.stores.library import StrategyLibraryStore


def configure_injector() -> DependencyInjector:
    """Hexagonal wiring: bind every port to its adapter."""
    injector = DependencyInjector()

    injector.bind(
        {
            # --- config ---
            Settings: Settings,
            # --- core ---
            Clock: SystemClock,
            Meter: NoopMeter,
            EventBus: RedisEventBus,
            Outbox: RedisOutbox,
            # --- auth ---
            UserRepository: PostgresUserRepository,
            ApiKeyRepository: PostgresApiKeyRepository,
            PasswordHasher: Pbkdf2PasswordHasher,
            TokenManager: JwtTokenManager,
            # --- marketdata ---
            CandleStore: ClickHouseCandleStore,
            CandleQueryPort: CandleQueryService,
            MarketDataSource: MarketDataSourceFactory,
            # --- signals ---
            FeatureComputer: PandasFeatureComputer,
            # --- strategies ---
            StrategyStore: StrategyLibraryStore,
            # --- backtest (cross-slice seams) ---
            BacktestDataStore: ClickHouseCandleStore,
            BacktestFeatureComputer: PandasFeatureComputer,
            StrategyGateway: StrategyManager,
            # --- risk ---
            RiskProfileStore: RedisRiskProfileStore,
        }
    )

    return injector
