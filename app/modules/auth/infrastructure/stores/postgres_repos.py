"""PostgreSQL auth stores — SQLAlchemy async repositories implementing auth ports.

Schema-per-context: these models live in the `auth` schema. Repositories take a
session factory and open a short-lived session per operation, so a single
connection pool is shared without sharing a session across concurrent requests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Integer, String, Text, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.infrastructure.capability.database.postgres import PostgresConnection
from app.modules.auth.domain.entities import ApiKey, Role, User


class AuthBase(DeclarativeBase):
    pass


class UserRow(AuthBase):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16), default=Role.VIEWER.value)
    disabled: Mapped[int] = mapped_column(Integer, default=0)


class ApiKeyRow(AuthBase):
    __tablename__ = "api_keys"
    __table_args__ = {"schema": "auth"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(index=True)
    key_prefix: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hashed_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(Integer)  # epoch seconds
    revoked: Mapped[int] = mapped_column(Integer, default=0)


class PostgresUserRepository:
    async def __connect__(self) -> None:
        pass

    async def __disconnect__(self) -> None:
        pass

    def __init__(self, postgres: PostgresConnection) -> None:
        self._session_factory = postgres.session_factory

    async def get_by_username(self, username: str) -> User | None:
        async with self._session_factory() as session:
            row = await session.scalar(select(UserRow).where(UserRow.username == username))
        return self._to_domain(row) if row else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        async with self._session_factory() as session:
            row = await session.get(UserRow, user_id)
        return self._to_domain(row) if row else None

    async def save(self, user: User) -> None:
        async with self._session_factory() as session:
            session.add(
                UserRow(
                    id=user.id,
                    username=user.username,
                    password_hash=user.password_hash,
                    role=user.role.value,
                    disabled=int(user.disabled),
                )
            )
            await session.commit()

    @staticmethod
    def _to_domain(row: UserRow) -> User:
        return User(
            id=row.id,
            username=row.username,
            password_hash=row.password_hash,
            role=Role(row.role),
            disabled=bool(row.disabled),
        )


class PostgresApiKeyRepository:
    async def __connect__(self) -> None:
        pass

    async def __disconnect__(self) -> None:
        pass

    def __init__(self, postgres: PostgresConnection) -> None:
        self._session_factory = postgres.session_factory

    async def save(self, api_key: ApiKey) -> None:
        async with self._session_factory() as session:
            session.add(
                ApiKeyRow(
                    id=api_key.id,
                    user_id=api_key.user_id,
                    key_prefix=api_key.key_prefix,
                    hashed_key=api_key.hashed_key,
                    created_at=int(api_key.created_at.timestamp()),
                    revoked=int(api_key.revoked),
                )
            )
            await session.commit()

    async def find_by_prefix(self, key_prefix: str) -> ApiKey | None:
        async with self._session_factory() as session:
            row = await session.scalar(select(ApiKeyRow).where(ApiKeyRow.key_prefix == key_prefix))
        return self._to_domain(row) if row else None

    async def revoke(self, key_id: UUID) -> None:
        async with self._session_factory() as session:
            row = await session.get(ApiKeyRow, key_id)
            if row is not None:
                row.revoked = 1
                await session.commit()

    async def list_by_user(self, user_id: UUID) -> list[ApiKey]:
        async with self._session_factory() as session:
            rows = (await session.scalars(select(ApiKeyRow).where(ApiKeyRow.user_id == user_id))).all()
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: ApiKeyRow) -> ApiKey:
        return ApiKey(
            id=row.id,
            user_id=row.user_id,
            key_prefix=row.key_prefix,
            hashed_key=row.hashed_key,
            created_at=datetime.fromtimestamp(row.created_at, UTC),
            revoked=bool(row.revoked),
        )
