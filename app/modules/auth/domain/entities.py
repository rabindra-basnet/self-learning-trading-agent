"""auth domain: entities and value objects (zero provider imports)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class Role(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    username: str
    password_hash: str
    role: Role = Role.VIEWER
    disabled: bool = False


@dataclass(frozen=True, slots=True)
class ApiKey:
    id: UUID
    user_id: UUID
    key_prefix: str
    hashed_key: str
    created_at: datetime
    revoked: bool = False


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in_sec: int
    token_type: str = "bearer"


@dataclass(frozen=True, slots=True)
class TokenClaims:
    subject: UUID
    role: Role
    token_type: str
    expires_at: datetime


def new_user(*, id: UUID | None = None, username: str, password_hash: str, role: Role) -> User:
    return User(id=id or uuid4(), username=username, password_hash=password_hash, role=role)
