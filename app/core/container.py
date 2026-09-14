"""Minimal DI container — composition root wiring, override-ready for tests.

Adapted from doc: application/domain depend on ports; the composition root
(`app/api/di.py`) and tests provide implementations.

NOTE: this is the small, in-house seam used only until the `di`-library port
lands (see app/api/di.py). It intentionally keeps a trivial surface so the
substitution is mechanical.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

from app.core.exceptions.taxonomy import ConfigurationError

T = TypeVar("T")

Factory = Callable[[], Any]


class Container:
    def __init__(self) -> None:
        self._registry: dict[type[Any], Factory] = {}
        self._singletons: dict[type[Any], Any] = {}

    def register(self, interface: type[T], factory: Factory) -> None:
        self._registry[interface] = factory

    def register_instance(self, interface: type[T], instance: Any) -> None:
        self._registry[interface] = lambda: instance
        self._singletons[interface] = instance

    def override(self, interface: type[T], instance: Any) -> None:
        """Test seam — temporarily replace implementation for a port."""
        self._registry[interface] = lambda: instance

    def resolve(self, interface: type[T]) -> T:
        if interface in self._singletons:
            return cast(T, self._singletons[interface])
        factory = self._registry.get(interface)
        if factory is None:
            raise ConfigurationError(f"No implementation registered for {interface.__name__}")
        instance: Any = factory()
        self._singletons[interface] = instance
        return cast(T, instance)
