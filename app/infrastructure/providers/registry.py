"""Provider registry: ``(capability, provider) -> adapter factory``.

Docs: `docs/INTEGRATION-ARCHITECTURE.md` §6 (configuration strategy) and §12
(adding / replacing a provider).

The composition root reads the configured provider name for a capability and
hot-wires the matching factory, so swapping or adding a vendor touches only its
boundary package plus one registry entry — never domain or application code.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

ProviderFactory = Callable[[], Any]


class UnknownProviderError(KeyError):
    """No factory registered for the requested ``(capability, provider)``."""


class ProviderRegistry:
    """In-memory registry of vendor adapter factories."""

    def __init__(self) -> None:
        self._factories: dict[tuple[str, str], ProviderFactory] = {}

    def register(self, capability: str, provider: str, factory: ProviderFactory) -> None:
        self._factories[(capability, provider)] = factory

    def create(self, capability: str, provider: str) -> Any:
        try:
            factory = self._factories[(capability, provider)]
        except KeyError:
            available = ", ".join(self.providers(capability)) or "<none>"
            raise UnknownProviderError(
                f"no {capability!r} provider registered for {provider!r} (available: {available})"
            ) from None
        return factory()

    def providers(self, capability: str) -> list[str]:
        return sorted(provider for cap, provider in self._factories if cap == capability)

    def capabilities(self) -> list[str]:
        return sorted({capability for capability, _ in self._factories})


provider_registry = ProviderRegistry()
