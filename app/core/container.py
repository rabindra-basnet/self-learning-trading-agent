"""Composition root facade over magic-di.

Every `register`/`resolve`/`override` call delegates to a
`magic_di.DependencyInjector`. Each interface gets one cached connectable
provider class; the injector owns the singleton instance and its lifecycle
(`connect()` / `disconnect()`), while routes keep reading from
`app.state.container` exactly as before.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

from magic_di import DependencyInjector

T = TypeVar("T")


class _Provided:
    """Singleton provider: builds the real instance from a closure factory.

    Implements the structural `ConnectableProtocol` (async `__connect__` /
    `__disconnect__`) so `magic_di` owns its lifecycle.
    """

    def __init__(self) -> None:
        self.instance: Any = self._factory()

    _factory: Callable[[], Any]

    async def __connect__(self) -> None:
        await self._lifecycle("__connect__")

    async def __disconnect__(self) -> None:
        if await self._lifecycle("__disconnect__"):
            return
        await self._lifecycle("dispose", "close")

    async def _lifecycle(self, *names: str) -> bool:
        wrapped = self.instance
        for name in names:
            method = getattr(wrapped, name, None)
            if method is None:
                continue
            result = method()
            if result is not None:
                await result
            return True
        return False


class Container:
    """Thin facade over a DependencyInjector instance."""

    def __init__(self) -> None:
        self._di = DependencyInjector()
        self._factories: dict[type[Any], Callable[[], Any]] = {}
        self._providers: dict[type[Any], type[_Provided]] = {}

    @property
    def injector(self) -> DependencyInjector:
        return self._di

    def register(self, interface: type[Any], make: Callable[[], Any]) -> None:
        """Bind `interface` to a connectable provider built once by `make()`."""
        self._factories[interface] = make
        self._providers.pop(interface, None)
        self._rebind(interface)

    def register_instance(self, interface: type[Any], instance: Any) -> None:
        self.register(interface, lambda: instance)

    def override(self, interface: type[Any], instance: Any) -> None:
        """Replace the binding for `interface` (test seam)."""
        self.register_instance(interface, instance)

    def resolve(self, interface: type[T]) -> T:
        provider = self._provider_for(interface)
        built = self._di.inject(provider)()
        return cast(T, built.instance)

    async def aresolve(self, interface: type[T]) -> T:
        return self.resolve(interface)

    async def connect(self) -> None:
        await self._di.connect()

    async def disconnect(self) -> None:
        await self._di.disconnect()

    def _rebind(self, interface: type[Any]) -> None:
        provider = self._provider_for(interface)
        self._di.bind({interface: provider})
        # Eager build so `connect()`/`disconnect()` reach the wrapped resource
        # and its underlying connection (`dispose()` / `close()`).
        self._di.inject(provider)()

    def _provider_for(self, interface: type[Any]) -> type[_Provided]:
        provider = self._providers.get(interface)
        if provider is None:
            make = self._factories[interface]
            name = f"_Provided[{interface.__name__}]"
            provider = cast(
                "type[_Provided]",
                type(
                    name,
                    (_Provided,),
                    {"__module__": __name__, "_factory": staticmethod(make)},
                ),
            )
            self._providers[interface] = provider
        return provider
