"""Market-data provider registry entries (docs/INTEGRATION-ARCHITECTURE.md A 12).

Adding an exchange (Kraken, Coinbase, ...) = add its boundary package and one
`provider_registry.register(...)` line here. No domain or application changes.
"""

from __future__ import annotations

from app.core.config.settings import Settings
from app.infrastructure.providers.registry import provider_registry
from app.modules.marketdata.domain.ports import MarketDataSource
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.adapter import TwelveDataMarketDataSource
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.config import TwelveDataConfig
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.adapter import YahooMarketDataSource
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.config import YahooConfig
from app.modules.marketdata.infrastructure.providers.exchange.binance.adapter import BinanceMarketDataSource
from app.modules.marketdata.infrastructure.providers.exchange.binance.config import BinanceConfig
from app.modules.marketdata.infrastructure.providers.exchange.kraken.adapter import KrakenMarketDataSource
from app.modules.marketdata.infrastructure.providers.exchange.kraken.config import KrakenConfig

CAPABILITY = "market_data"


def build_binance_market_data() -> MarketDataSource:
    return BinanceMarketDataSource(BinanceConfig())


def build_kraken_market_data() -> MarketDataSource:
    return KrakenMarketDataSource(KrakenConfig())


def build_yahoo_market_data() -> MarketDataSource:
    return YahooMarketDataSource(YahooConfig())


def build_twelvedata_market_data() -> MarketDataSource:
    return TwelveDataMarketDataSource(TwelveDataConfig())


def register_market_data_providers() -> None:
    provider_registry.register(CAPABILITY, "binance", build_binance_market_data)
    provider_registry.register(CAPABILITY, "kraken", build_kraken_market_data)
    provider_registry.register(CAPABILITY, "twelvedata", build_twelvedata_market_data)
    provider_registry.register(CAPABILITY, "yahoo", build_yahoo_market_data)


class MarketDataSourceFactory:
    def __init__(self, settings: Settings) -> None:
        self._provider = settings.market_data_provider
        self.instance = None

    async def __connect__(self) -> None:
        register_market_data_providers()
        self.instance = provider_registry.create(CAPABILITY, self._provider)

    async def __disconnect__(self) -> None:
        pass
