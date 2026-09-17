"""Market-data provider registry entries (docs/INTEGRATION-ARCHITECTURE.md §12).

Adding an exchange (Kraken, Coinbase, ...) = add its boundary package and one
`provider_registry.register(...)` line here. No domain or application changes.
"""

from __future__ import annotations

from app.infrastructure.providers.registry import provider_registry
from app.modules.marketdata.domain.ports import MarketDataSource
from app.modules.marketdata.infrastructure.providers.exchange.binance.adapter import (
    BinanceMarketDataSource,
)
from app.modules.marketdata.infrastructure.providers.exchange.binance.config import (
    BinanceConfig,
)

CAPABILITY = "market_data"


def build_binance_market_data() -> MarketDataSource:
    return BinanceMarketDataSource(BinanceConfig())


def register_market_data_providers() -> None:
    provider_registry.register(CAPABILITY, "binance", build_binance_market_data)
