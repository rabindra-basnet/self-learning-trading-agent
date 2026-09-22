from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.capability.database.base import Base
from app.infrastructure.capability.database.postgres import PostgresConnection
from app.modules.trading.domain.portfolio import Position


class PositionRow(Base):
    __tablename__ = "positions"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    average_entry_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False, default=Decimal("0"))


class PostgresPositionRepository:
    def __init__(self, postgres: PostgresConnection) -> None:
        self._session_factory = postgres.session_factory

    async def get(self, symbol: str) -> Position | None:
        async with self._session_factory() as session:
            row = await session.get(PositionRow, symbol.upper())
        return self._to_domain(row) if row else None

    async def save(self, position: Position) -> None:
        symbol = position.symbol.upper()
        async with self._session_factory() as session:
            row = await session.get(PositionRow, symbol)
            if row is None:
                session.add(
                    PositionRow(
                        symbol=symbol,
                        quantity=position.quantity,
                        average_entry_price=position.average_entry_price,
                        realized_pnl=position.realized_pnl,
                    )
                )
            else:
                row.quantity = position.quantity
                row.average_entry_price = position.average_entry_price
                row.realized_pnl = position.realized_pnl
            await session.commit()

    @staticmethod
    def _to_domain(row: PositionRow) -> Position:
        return Position(
            symbol=row.symbol,
            quantity=Decimal(row.quantity),
            average_entry_price=Decimal(row.average_entry_price),
            realized_pnl=Decimal(row.realized_pnl),
        )
