"""Composition root over the `di` library (0.79.2) — real, scoped DI.

The `Container` facade retains the `register/resolve` surface the existing
code relies on, but every resolution delegates to a `di.Container` through
explicit `ScopeState`s. FastAPI glue lives in `app/api/di.py`; routes stop
depending on `fastapi.Depends`.
"""

from __future__ import annotations

from collections.abc import Callable

from di.api.scopes import Scope

from di import Container as DiContainer
from di import ScopeState

T = object


class Container:
    def __init__(self) -> None:
        self._di = DiContainer()
        self._app_state = ScopeState()
        self._app_state.enter_scope(Scope.APP)

    def register(self, interface: type, factory: Callable[..., object]) -> None:
        def _factory() -> object:
            return factory()

        self._di.bind(_factory, provided_by=interface, scope=Scope.APP)

    def register_instance(self, interface: type, instance: object) -> None:
        def _factory() -> object:
            return instance

        self._di.bind(_factory, provided_by=interface, scope=Scope.APP)

    def override(self, interface: type, instance: object) -> None:
        """Test seam — substitute an implementation for a port."""
        self.register_instance(interface, instance)

    def resolve(self, interface: type, state: ScopeState | None = None) -> object:
        scope_state = state if state is not None else self._app_state
        solved = self._di.solve(interface, scope=Scope.REQUEST, state=scope_state)
        return self._di.execute_sync(solved, scope_state)

    async def aresolve(self, interface: type, state: ScopeState | None = None) -> object:
        scope_state = state if state is not None else self._app_state
        solved = self._di.solve(interface, scope=Scope.REQUEST, state=scope_state)
        return await self._di.execute_async(solved, scope_state)

    def enter_scope(self) -> ScopeState:
        state = ScopeState(self._app_state)
        state.enter_scope(Scope.REQUEST)
        return state