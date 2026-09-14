"""In-memory auth stores — legit adapters for dev/tests (implements ports)."""

from __future__ import annotations

from dataclasses import replace

from app.modules.auth.domain.entities import ApiKey, User


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}
        self._by_username: dict[str, User] = {}

    async def get_by_username(self, username: str) -> User | None:
        return self._by_username.get(username)

    async def get_by_id(self, user_id) -> User | None:
        return self._by_id.get(str(user_id))

    async def save(self, user: User) -> None:
        self._by_id[str(user.id)] = user
        self._by_username[user.username] = user


class InMemoryApiKeyRepository:
    def __init__(self) -> None:
        self._keys: dict[str, ApiKey] = {}

    async def save(self, api_key: ApiKey) -> None:
        self._keys[str(api_key.id)] = api_key

    async def find_by_prefix(self, key_prefix: str) -> ApiKey | None:
        return next((k for k in self._keys.values() if k.key_prefix == key_prefix), None)

    async def revoke(self, key_id) -> None:
        key = self._keys.get(str(key_id))
        if key is not None:
            self._keys[str(key_id)] = replace(key, revoked=True)

    async def list_by_user(self, user_id) -> list[ApiKey]:
        return [k for k in self._keys.values() if str(k.user_id) == str(user_id)]
