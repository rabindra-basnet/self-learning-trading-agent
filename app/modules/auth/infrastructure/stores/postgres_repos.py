"""PostgreSQL auth stores — SQLAlchemy async repositories implementing auth ports.

Schema-per-context: these models live in the `auth` schema (Alembic migration).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> User | None:
        row = await self._session.scalar(select(UserRow).where(UserRow.username == username))
        return self._to_domain(row) if row else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserRow, user_id)
        return self._to_domain(row) if row else None

    async def save(self, user: User) -> None:
        self._session.add(
            UserRow(
                id=user.id,
                username=user.username,
                password_hash=user.password_hash,
                role=user.role.value,
                disabled=int(user.disabled),
            )
        )
        await self._session.flush()

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
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, api_key: ApiKey) -> None:
        self._session.add(
            ApiKeyRow(
                id=api_key.id,
                user_id=api_key.user_id,
                key_prefix=api_key.key_prefix,
                hashed_key=api_key.hashed_key,
                created_at=int(api_key.created_at.timestamp()),
                revoked=int(api_key.revoked),
            )
        )
        await self._session.flush()

    async def find_by_prefix(self, key_prefix: str) -> ApiKey | None:
        row = await self._session.scalar(select(ApiKeyRow).where(ApiKeyRow.key_prefix == key_prefix))
        return self._to_domain(row) if row else None

    async def revoke(self, key_id: UUID) -> None:
        row = await self._session.get(ApiKeyRow, key_id)
        if row is not None:
            row.revoked = 1
            await self._session.flush()

    async def list_by_user(self, user_id: UUID) -> list[ApiKey]:
        rows = (await self._session.scalars(select(ApiKeyRow).where(ApiKeyRow.user_id == user_id))).all()
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: ApiKeyRow) -> ApiKey:
        from datetime import UTC, datetime

        return ApiKey(
            id=row.id,
            user_id=row.user_id,
            key_prefix=row.key_prefix,
            hashed_key=row.hashed_key,
            created_at=datetime.fromtimestamp(row.created_at, UTC),
            revoked=bool(row.revoked),
        )
