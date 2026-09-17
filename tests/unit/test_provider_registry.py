"""Provider registry behaviour — the (capability, provider) -> factory seam."""

from __future__ import annotations

import pytest
from app.infrastructure.providers.registry import ProviderRegistry, UnknownProviderError

pytestmark = pytest.mark.unit


def test_register_and_create_returns_factory_output() -> None:
    registry = ProviderRegistry()
    sentinel = object()
    registry.register("market_data", "fake", lambda: sentinel)
    assert registry.create("market_data", "fake") is sentinel


def test_unknown_provider_lists_alternatives() -> None:
    registry = ProviderRegistry()
    registry.register("market_data", "binance", lambda: object())
    with pytest.raises(UnknownProviderError, match="available: binance"):
        registry.create("market_data", "not-a-vendor")


def test_unknown_capability_reports_no_providers() -> None:
    registry = ProviderRegistry()
    with pytest.raises(UnknownProviderError, match=r"available: <none>"):
        registry.create("news", "rss")


def test_providers_and_capabilities_are_scoped_and_sorted() -> None:
    registry = ProviderRegistry()
    registry.register("market_data", "yahoo", lambda: object())
    registry.register("market_data", "kraken", lambda: object())
    registry.register("news", "rss", lambda: object())
    assert registry.providers("market_data") == ["kraken", "yahoo"]
    assert registry.providers("news") == ["rss"]
    assert registry.capabilities() == ["market_data", "news"]


def test_registering_twice_replaces_the_factory() -> None:
    registry = ProviderRegistry()
    registry.register("market_data", "yahoo", lambda: "old")
    registry.register("market_data", "yahoo", lambda: "new")
    assert registry.create("market_data", "yahoo") == "new"
