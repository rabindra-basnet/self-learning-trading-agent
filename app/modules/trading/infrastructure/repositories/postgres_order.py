from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Numeric, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.capability.database.base import Base
from app.infrastructure.capability.database.postgres import PostgresConnection
from app.modules.trading.domain.entities import TradeOrder
from app.modules.trading.domain.value_objects.order import OrderSide, OrderStatus, OrderType


class TradeOrderRow(Base):
    __tablename__ = "trade_orders"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    executed_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    client_order_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)


class PostgresOrderRepository:
    def __init__(self, postgres: PostgresConnection) -> None:
        self._session_factory = postgres.session_factory

    async def get(self, order_id: UUID) -> TradeOrder | None:
        async with self._session_factory() as session:
            row = await session.get(TradeOrderRow, order_id)
        return self._to_domain(row) if row else None

    async def get_by_client_order_id(self, client_order_id: str) -> TradeOrder | None:
        async with self._session_factory() as session:
            row = await session.scalar(select(TradeOrderRow).where(TradeOrderRow.client_order_id == client_order_id))
        return self._to_domain(row) if row else None

    async def save(self, order: TradeOrder) -> None:
        async with self._session_factory() as session:
            row = await session.get(TradeOrderRow, order.id)
            if row is None:
                session.add(self._to_row(order))
            else:
                row.symbol = order.symbol
                row.side = order.side.value
                row.quantity = order.quantity
                row.order_type = order.order_type.value
                row.status = order.status.value
                row.requested_price = order.requested_price
                row.executed_price = order.executed_price
                row.client_order_id = order.client_order_id
                row.created_at = order.created_at
                row.rejection_reason = order.rejection_reason
            await session.commit()

    @staticmethod
    def _to_row(order: TradeOrder) -> TradeOrderRow:
        return TradeOrderRow(
            id=order.id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            order_type=order.order_type.value,
            status=order.status.value,
            requested_price=order.requested_price,
            executed_price=order.executed_price,
            client_order_id=order.client_order_id,
            created_at=order.created_at,
            rejection_reason=order.rejection_reason,
        )

    @staticmethod
    def _to_domain(row: TradeOrderRow) -> TradeOrder:
        return TradeOrder(
            id=row.id,
            symbol=row.symbol,
            side=OrderSide(row.side),
            quantity=Decimal(row.quantity),
            order_type=OrderType(row.order_type),
            status=OrderStatus(row.status),
            requested_price=Decimal(row.requested_price),
            executed_price=Decimal(row.executed_price) if row.executed_price is not None else None,
            client_order_id=row.client_order_id,
            created_at=row.created_at,
            rejection_reason=row.rejection_reason,
        )
