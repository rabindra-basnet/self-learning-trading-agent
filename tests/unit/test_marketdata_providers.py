"""Market-data boundary tests: vendor payload -> domain model normalization.

Fixtures mirror the recorded vendor payload shapes (docs/INTEGRATION-ARCHITECTURE.md §11);
no network IO.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from app.core.exceptions.taxonomy import MalformedDataError
from app.infrastructure.providers.registry import provider_registry
from app.modules.marketdata.domain.entities import Symbol, Timeframe
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.config import (
    TwelveDataConfig,
)
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.dtos import (
    TwelveQuote,
    TwelveTimeSeries,
)
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.mapping import (
    parse_datetime,
)
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.mapping import (
    to_candles as twelve_to_candles,
)
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.mapping import (
    to_ticker as twelve_to_ticker,
)
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.dtos import YahooEnvelope
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.errors import (
    handle_yahoo_error,
)
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.mapping import (
    to_candles as yahoo_to_candles,
)
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.mapping import (
    to_ticker as yahoo_to_ticker,
)
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.mapping import (
    to_yahoo_symbol,
)
from app.modules.marketdata.infrastructure.providers.exchange.kraken.errors import (
    handle_kraken_errors,
)
from app.modules.marketdata.infrastructure.providers.exchange.kraken.mapping import (
    first_entry,
    to_kraken_pair,
)
from app.modules.marketdata.infrastructure.providers.exchange.kraken.mapping import (
    to_candles as kraken_to_candles,
)
from app.modules.marketdata.infrastructure.providers.exchange.kraken.mapping import (
    to_ticker as kraken_to_ticker,
)
from app.modules.marketdata.infrastructure.providers.registry import (
    register_market_data_providers,
)
from pydantic import ValidationError

pytestmark = pytest.mark.unit

YAHOO_PAYLOAD: dict[str, Any] = {
    "chart": {
        "result": [
            {
                "meta": {
                    "symbol": "BTC-USD",
                    "currency": "USD",
                    "regularMarketPrice": 64000.5,
                    "regularMarketTime": 1710003600,
                },
                "timestamp": [1710000000, 1710003600],
                "indicators": {
                    "quote": [
                        {
                            "open": [1.0, None],
                            "high": [2.0, None],
                            "low": [0.5, None],
                            "close": [1.5, None],
                            "volume": [10.0, None],
                        }
                    ]
                },
            }
        ],
        "error": None,
    }
}


def test_yahoo_symbol_aliases_usdt_to_usd() -> None:
    assert to_yahoo_symbol(Symbol.of("btc/usdt")) == "BTC-USD"
    assert to_yahoo_symbol(Symbol.of("eth/usd")) == "ETH-USD"


def test_yahoo_candles_skip_null_padding_and_normalize() -> None:
    chart = YahooEnvelope.model_validate(YAHOO_PAYLOAD).chart.result[0]  # type: ignore[index]
    candles = yahoo_to_candles(chart, Symbol.of("BTC/USDT"), Timeframe.H1)
    assert len(candles) == 1
    candle = candles[0]
    assert candle.opened_at == datetime.fromtimestamp(1710000000, UTC)
    assert candle.close == Decimal("1.5")
    assert candle.volume == Decimal("10.0")
    assert candle.exchange == "yahoo"


def test_yahoo_ticker_collapses_bid_ask_to_last_price() -> None:
    chart = YahooEnvelope.model_validate(YAHOO_PAYLOAD).chart.result[0]  # type: ignore[index]
    ticker = yahoo_to_ticker(chart, Symbol.of("BTC/USDT"))
    assert ticker.last == ticker.bid == ticker.ask == Decimal("64000.5")
    assert ticker.volume_24h == Decimal(0)


def test_yahoo_payload_error_maps_to_rate_limited() -> None:
    error = handle_yahoo_error({"code": "429", "description": "Too Many Requests"})
    assert error.error_code == "rate_limited"
    assert error.provider == "yahoo"


def test_kraken_pair_aliases_btc_to_xbt() -> None:
    assert to_kraken_pair(Symbol.of("btc/usdt")) == "XBTUSDT"
    assert to_kraken_pair(Symbol.of("eth/usd")) == "ETHUSD"


def test_kraken_candles_map_columns_in_order() -> None:
    rows = [[1710000000, "1.0", "2.0", "0.5", "1.5", "1.4", "100.0", 5]]
    candles = kraken_to_candles(rows, Symbol.of("BTC/USDT"), Timeframe.H1)
    assert len(candles) == 1
    assert candles[0].high == Decimal("2.0")
    assert candles[0].volume == Decimal("100.0")


def test_kraken_ticker_uses_bid_ask_and_rolling_volume() -> None:
    entry: dict[str, Any] = {"a": ["1.6", "1", "1"], "b": ["1.5", "1", "1"], "c": ["1.55", "0.1"], "v": ["10", "250"]}
    now = datetime(2024, 3, 9, 12, 0, tzinfo=UTC)
    ticker = kraken_to_ticker(entry, Symbol.of("BTC/USDT"), now)
    assert ticker.bid == Decimal("1.5")
    assert ticker.ask == Decimal("1.6")
    assert ticker.volume_24h == Decimal("250")


def test_kraken_error_strings_map_to_domain_errors() -> None:
    assert handle_kraken_errors(["EAPI:Rate limit exceeded"]).error_code == "rate_limited"
    assert handle_kraken_errors(["EQuery:Unknown asset pair"]).error_code == "provider_validation"


def test_kraken_first_entry_ignores_last_cursor() -> None:
    result: dict[str, Any] = {"last": 1710000000, "XXBTZUSD": {"a": ["1"]}}
    assert first_entry(result) == {"a": ["1"]}


def test_twelve_data_timestamps_accept_intraday_and_daily() -> None:
    assert parse_datetime("2024-03-09 12:30:00") == datetime(2024, 3, 9, 12, 30, tzinfo=UTC)
    assert parse_datetime("2024-03-09") == datetime(2024, 3, 9, tzinfo=UTC)
    with pytest.raises(MalformedDataError):
        parse_datetime("09/03/2024")


def test_twelve_data_reverses_newest_first_payload() -> None:
    series = TwelveTimeSeries.model_validate(
        {
            "status": "ok",
            "values": [
                {
                    "datetime": "2024-03-09 12:00:00",
                    "open": "2",
                    "high": "3",
                    "low": "1",
                    "close": "2.5",
                    "volume": "5",
                },
                {
                    "datetime": "2024-03-09 11:00:00",
                    "open": "1",
                    "high": "2",
                    "low": "0.5",
                    "close": "1.5",
                    "volume": "4",
                },
            ],
        }
    )
    candles = twelve_to_candles(series.values, Symbol.of("BTC/USD"), Timeframe.H1)
    assert [c.opened_at.hour for c in candles] == [11, 12]
    assert candles[0].close == Decimal("1.5")


def test_twelve_data_ticker_falls_back_to_last_price() -> None:
    quote = TwelveQuote.model_validate({"symbol": "BTC/USD", "close": "64000.0", "timestamp": 1710000000})
    ticker = twelve_to_ticker(quote, Symbol.of("BTC/USD"), datetime.now(UTC))
    assert ticker.last == ticker.bid == ticker.ask == Decimal("64000.0")


def test_twelve_data_requires_api_key_even_with_env_file_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKET_DATA_TWELVEDATA_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        TwelveDataConfig(_env_file=None)


def test_registry_exposes_every_market_data_vendor() -> None:
    register_market_data_providers()
    assert provider_registry.providers("market_data") == ["binance", "kraken", "twelvedata", "yahoo"]
