"""Container facade smoke tests — no external IO."""

from __future__ import annotations

import pytest
from app.core.container import Container

pytestmark = pytest.mark.unit


class _Resource:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def test_register_instance_is_singleton() -> None:
    container = Container()
    resource = _Resource()
    container.register_instance(_Resource, resource)
    assert container.resolve(_Resource) is resource
    assert container.resolve(_Resource) is resource


def test_factory_is_called_once() -> None:
    container = Container()
    calls: list[int] = []

    def make() -> _Resource:
        calls.append(1)
        return _Resource()

    container.register(_Resource, make)
    first = container.resolve(_Resource)
    assert calls == [1]
    assert container.resolve(_Resource) is first


def test_unknown_interface_raises() -> None:
    with pytest.raises(KeyError):
        Container().resolve(_Resource)


def test_override_swaps_binding() -> None:
    container = Container()
    original = _Resource()
    replacement = _Resource()
    container.register_instance(_Resource, original)
    container.override(_Resource, replacement)
    assert container.resolve(_Resource) is replacement


async def test_disconnect_closes_resource() -> None:
    container = Container()
    resource = _Resource()
    container.register_instance(_Resource, resource)
    await container.connect()
    await container.disconnect()
    assert resource.closed is True
