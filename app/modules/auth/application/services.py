"""auth application: use-cases. Depend only on ports; return Result[T, DomainError]."""

from __future__ import annotations

import secrets

from app.core.common.clock import Clock
from app.core.common.result import Err, Ok, Result
from app.core.exceptions.taxonomy import AuthenticationError, DomainError
from app.modules.auth.domain.entities import ApiKey, Role, TokenClaims, TokenPair, User, new_user
from app.modules.auth.domain.ports import (
    ApiKeyRepository,
    PasswordHasher,
    TokenManager,
    UserRepository,
)

MIN_PASSWORD_LEN = 8
_DUPLICATE_USER = "user_exists"
_INVALID_CREDENTIALS = "invalid_credentials"


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenManager,
        clock: Clock,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock

    async def register(
        self,
        *,
        username: str,
        password: str,
        role: Role = Role.VIEWER,
    ) -> Result[User, DomainError]:
        username = username.strip().lower()
        if len(password) < MIN_PASSWORD_LEN:
            return Err(DomainError(f"password must be at least {MIN_PASSWORD_LEN} characters"))
        if await self._users.get_by_username(username) is not None:
            return Err(DomainError(_DUPLICATE_USER, provider="auth"))
        user = new_user(username=username, password_hash=self._hasher.hash(password), role=role)
        await self._users.save(user)
        return Ok(user)

    async def login(self, *, username: str, password: str) -> Result[TokenPair, DomainError]:
        username = username.strip().lower()
        user = await self._users.get_by_username(username)
        if user is None or not self._hasher.verify(password, user.password_hash):
            return Err(DomainError(_INVALID_CREDENTIALS, provider="auth"))
        if user.disabled:
            return Err(DomainError("user_disabled", provider="auth"))
        pair = await self._tokens.issue(user)
        return Ok(pair)

    async def refresh(self, refresh_token: str) -> Result[TokenPair, DomainError]:
        try:
            claims = await self._tokens.verify_refresh(refresh_token)
        except AuthenticationError as exc:
            return Err(exc)
        user = await self._users.get_by_id(claims.subject)
        if user is None or user.disabled:
            return Err(DomainError("user_disabled", provider="auth"))
        pair = await self._tokens.issue(user, refresh_token=refresh_token)
        return Ok(pair)

    async def verify_access(self, token: str) -> Result[TokenClaims, DomainError]:
        try:
            claims = await self._tokens.verify_access(token)
        except AuthenticationError as exc:
            return Err(exc)
        return Ok(claims)


class ApiKeyService:
    def __init__(self, keys: ApiKeyRepository, users: UserRepository, hasher: PasswordHasher, clock: Clock) -> None:
        self._keys = keys
        self._users = users
        self._hasher = hasher
        self._clock = clock

    async def create(self, user_id, label: str) -> Result[tuple[ApiKey, str], DomainError]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            return Err(DomainError("user_not_found", provider="auth"))
        secret = secrets.token_urlsafe(24)
        raw = f"{label.lower().replace(' ', '-')}_{secret}"
        key = ApiKey(
            user_id=user.id,
            key_prefix=raw.split("_")[0],
            hashed_key=self._hasher.hash(raw),
            created_at=self._clock.utcnow(),
        )
        await self._keys.save(key)
        return Ok((key, secret))

    async def list(self, user_id) -> list[ApiKey]:
        return await self._keys.list_by_user(user_id)

    async def lookup(self, raw_key: str) -> ApiKey | None:
        prefix = raw_key.split("_")[0]
        stored = await self._keys.find_by_prefix(prefix)
        if stored is None or stored.revoked:
            return None
        if not self._hasher.verify(raw_key, stored.hashed_key):
            return None
        return stored

    async def revoke(self, key_id) -> None:
        await self._keys.revoke(key_id)
