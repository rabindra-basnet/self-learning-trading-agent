"""JWT provider adapter (PyJWT) — JwtTokenManager implements the TokenManager port.

All SDK/framework exceptions are mapped to domain `AuthenticationError` at this
boundary (docs/INTEGRATION-ARCHITECTURE.md §5/§9).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app.core.exceptions.taxonomy import AuthenticationError, ConfigurationError
from app.modules.auth.domain.entities import Role, TokenClaims, TokenPair, User


@dataclass(frozen=True, slots=True)
class JwtTokenManager:
    secret: str
    access_ttl_min: int = 15
    refresh_ttl_days: int = 7
    algorithm: str = "HS256"

    def __post_init__(self) -> None:
        if len(self.secret) < 16:
            raise ConfigurationError("JwtTokenManager secret must be at least 16 characters")

    async def issue(self, user: User, refresh_token: str | None = None) -> TokenPair:
        now = datetime.now(UTC)
        access_exp = now + timedelta(minutes=self.access_ttl_min)
        refresh_exp = now + timedelta(days=self.refresh_ttl_days)
        access = jwt.encode(
            {
                "sub": str(user.id),
                "role": user.role.value,
                "type": "access",
                "iat": now,
                "exp": access_exp,
            },
            self.secret,
            algorithm=self.algorithm,
        )
        refresh = jwt.encode(
            {
                "sub": str(user.id),
                "type": "refresh",
                "iat": now,
                "exp": refresh_exp,
                "jti": str(uuid4()),
            },
            self.secret,
            algorithm=self.algorithm,
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in_sec=int((access_exp - now).total_seconds()),
        )

    async def verify_access(self, token: str) -> TokenClaims:
        return self._verify(token, expected="access")

    async def verify_refresh(self, token: str) -> TokenClaims:
        return self._verify(token, expected="refresh")

    def _verify(self, token: str, *, expected: str) -> TokenClaims:
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("token_expired", provider="jwt", cause=exc) from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("token_invalid", provider="jwt", cause=exc) from exc
        if payload.get("type") != expected:
            raise AuthenticationError("token_type_mismatch", provider="jwt")
        try:
            return TokenClaims(
                subject=payload["sub"],
                role=Role(payload["role"]),
                token_type=expected,
                expires_at=datetime.fromtimestamp(payload["exp"], UTC),
            )
        except (KeyError, ValueError) as exc:
            raise AuthenticationError("token_claims_malformed", provider="jwt", cause=exc) from exc
