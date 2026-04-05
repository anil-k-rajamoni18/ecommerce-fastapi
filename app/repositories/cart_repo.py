from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart, CartItem


class CartRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: UUID) -> Cart | None:
        result = await self.db.execute(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
        )
        return result.scalar_one_or_none()

    async def get_item_by_id(self, item_id: UUID) -> CartItem | None:
        result = await self.db.execute(
            select(CartItem)
            .where(CartItem.id == item_id)
            .options(selectinload(CartItem.product))
        )
        return result.scalar_one_or_none()

    async def get_item_by_product(self, cart_id: UUID, product_id: UUID) -> CartItem | None:
        result = await self.db.execute(
            select(CartItem).where(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
        )
        return result.scalar_one_or_none()

    async def create_cart(self, user_id: UUID) -> Cart:
        cart = Cart(user_id=user_id)
        self.db.add(cart)
        await self.db.flush()
        await self.db.refresh(cart)
        cart.items = []
        return cart

    async def save_item(self, item: CartItem) -> CartItem:
        self.db.add(item)
        await self.db.flush()
        return item

    async def delete_item(self, item: CartItem) -> None:
        await self.db.delete(item)
        await self.db.flush()

    async def clear_items(self, cart: Cart) -> None:
        for item in cart.items:
            await self.db.delete(item)
        await self.db.flush()