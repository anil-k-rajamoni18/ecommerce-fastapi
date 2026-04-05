from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem
from app.models.payment import Payment


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _base_query(self):
        return (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.payment),
            )
        )

    async def get_by_id(self, order_id: UUID) -> Order | None:
        result = await self.db.execute(self._base_query().where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID, offset: int, limit: int) -> tuple[list[Order], int]:
        total = (
            await self.db.execute(select(func.count()).select_from(Order).where(Order.user_id == user_id))
        ).scalar_one()
        result = await self.db.execute(
            self._base_query()
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all(), total

    async def list_all(self, offset: int, limit: int) -> tuple[list[Order], int]:
        total = (await self.db.execute(select(func.count()).select_from(Order))).scalar_one()
        result = await self.db.execute(
            self._base_query()
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all(), total

    async def save(self, order: Order) -> Order:
        self.db.add(order)
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def save_items(self, items: list[OrderItem]) -> None:
        for item in items:
            self.db.add(item)
        await self.db.flush()

    async def save_payment(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.flush()
        return payment